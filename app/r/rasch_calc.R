#!/usr/bin/env Rscript

suppressWarnings(suppressMessages({
  library(ltm)
  library(jsonlite)
}))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  msg <- list(error = "CSV fayl yo'li berilmadi")
  cat(toJSON(msg, auto_unbox = TRUE))
  quit(status = 2)
}

csv_path <- args[[1]]

safe_stop <- function(message, status = 1) {
  msg <- list(error = message)
  cat(toJSON(msg, auto_unbox = TRUE))
  quit(status = status)
}

# Read CSV (no header), allow missing as blank -> NA
x <- tryCatch({
  read.csv(csv_path, header = FALSE, sep = ",", na.strings = c("", "NA"))
}, error = function(e) e)

if (inherits(x, "error")) {
  safe_stop(paste("CSV o'qishda xato:", x$message), status = 2)
}

# Ensure numeric 0/1/NA
for (j in seq_len(ncol(x))) {
  x[[j]] <- suppressWarnings(as.integer(as.character(x[[j]])))
}

if (nrow(x) == 0 || ncol(x) == 0) {
  safe_stop("Matritsa bo'sh")
}

# Fit Rasch model (MMLE in ltm)
fit <- tryCatch({
  rasch(as.matrix(x), IRT.param = TRUE)
}, error = function(e) e)

if (inherits(fit, "error")) {
  safe_stop(paste("Model moslashtirishda xato:", fit$message))
}

# Item parameters (difficulty)
item_coefs <- coef(fit)
# Attempt to standardize column name for difficulty
if (is.matrix(item_coefs)) {
  diff_col <- NULL
  if ("Dffclt" %in% colnames(item_coefs)) diff_col <- "Dffclt"
  if (is.null(diff_col) && "difficulty" %in% tolower(colnames(item_coefs))) {
    diff_col <- colnames(item_coefs)[tolower(colnames(item_coefs)) == "difficulty"][1]
  }
  if (is.null(diff_col)) {
    # fall back: if single column, take it; else first column
    diff_col <- colnames(item_coefs)[1]
  }
  items <- lapply(seq_len(nrow(item_coefs)), function(i) {
    list(
      item_id = paste0("Item", i),
      difficulty = unname(as.numeric(item_coefs[i, diff_col]))
    )
  })
} else {
  # Unexpected structure
  items <- lapply(seq_along(item_coefs), function(i) {
    list(
      item_id = names(item_coefs)[i],
      difficulty = unname(as.numeric(item_coefs[i]))
    )
  })
}

# Person scores via factor.scores (EAP). This returns unique patterns; expand to per-person preserving order.
fs <- tryCatch({
  factor.scores(fit, resp.patterns = as.data.frame(x), method = "EAP")
}, error = function(e) e)

if (inherits(fs, "error")) {
  safe_stop(paste("Person skorlari hisoblashda xato:", fs$message))
}

score_dat <- fs$score.dat
# Identify the columns that correspond to items (first k columns)
num_items <- ncol(x)
# Build keys for patterns
pattern_key <- function(row) paste(row, collapse = "|")

# Map pattern -> (eap, se)
if (!is.null(score_dat)) {
  # score_dat typically has item columns followed by z1 and se.z1
  # detect by position
  eap_col <- "z1"
  se_col <- "se.z1"
  # Some versions might name differently; fallback to last two columns
  if (!(eap_col %in% colnames(score_dat))) {
    eap_col <- tail(colnames(score_dat), 1)
  }
  if (!(se_col %in% colnames(score_dat))) {
    se_col <- tail(colnames(score_dat), 2)[1]
  }

  patt_cols <- seq_len(num_items)
  patt_keys <- apply(score_dat[, patt_cols, drop = FALSE], 1, pattern_key)
  eap_vals <- as.numeric(score_dat[[eap_col]])
  se_vals <- suppressWarnings(as.numeric(score_dat[[se_col]]))
  if (length(se_vals) != length(eap_vals) || any(is.na(se_vals))) {
    se_vals <- rep(NA_real_, length(eap_vals))
  }
  patt_to_score <- setNames(
    lapply(seq_along(patt_keys), function(i) list(eap = eap_vals[i], se = se_vals[i])),
    patt_keys
  )

  persons <- lapply(seq_len(nrow(x)), function(i) {
    key <- pattern_key(x[i, , drop = TRUE])
    sc <- patt_to_score[[key]]
    if (is.null(sc)) sc <- list(eap = NA_real_, se = NA_real_)
    list(person_index = i, eap = unname(as.numeric(sc$eap)), se = unname(as.numeric(sc$se)))
  })
} else {
  persons <- lapply(seq_len(nrow(x)), function(i) list(person_index = i, eap = NA_real_, se = NA_real_))
}

# Fit stats
fit_stats <- tryCatch({
  ll <- as.numeric(logLik(fit))
  aic <- AIC(fit)
  bic <- BIC(fit)
  list(logLik = ll, AIC = as.numeric(aic), BIC = as.numeric(bic), n_obs = nrow(x), n_items = ncol(x))
}, error = function(e) list(n_obs = nrow(x), n_items = ncol(x)))

result <- list(
  items = items,
  persons = persons,
  fit = fit_stats
)

cat(toJSON(result, auto_unbox = TRUE, digits = 6, na = "null"))
