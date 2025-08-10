import io
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import tempfile
from typing import Dict, List, Any
import numpy as np

def create_rasch_pdf_report(data: Dict[str, Any]) -> bytes:
    """
    Rasch model natijalaridan PDF hisobot yaratadi
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    # Stilni o'rnatish
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.darkblue
    )
    
    # Sarlavha
    story.append(Paragraph("Rasch Model Tahlil Natijalari", title_style))
    story.append(Spacer(1, 20))
    
    # Umumiy ma'lumotlar
    fit_stats = data.get('fit', {})
    story.append(Paragraph("Umumiy Ma'lumotlar", heading_style))
    
    general_info = [
        ["Parametr", "Qiymat"],
        ["Kuzatuvlar soni", str(fit_stats.get('n_obs', 'N/A'))],
        ["Itemlar soni", str(fit_stats.get('n_items', 'N/A'))],
        ["Log-Likelihood", f"{fit_stats.get('logLik', 'N/A'):.3f}" if fit_stats.get('logLik') else 'N/A'],
        ["AIC", f"{fit_stats.get('AIC', 'N/A'):.3f}" if fit_stats.get('AIC') else 'N/A'],
        ["BIC", f"{fit_stats.get('BIC', 'N/A'):.3f}" if fit_stats.get('BIC') else 'N/A']
    ]
    
    general_table = Table(general_info, colWidths=[2*inch, 2*inch])
    general_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(general_table)
    story.append(Spacer(1, 20))
    
    # Item parametrlari
    items = data.get('items', [])
    if items:
        story.append(Paragraph("Item Parametrlari (Qiyinchilik)", heading_style))
        
        item_data = [["Item ID", "Qiyinchilik"]]
        for item in items:
            item_data.append([
                item.get('item_id', 'N/A'),
                f"{item.get('difficulty', 0):.3f}"
            ])
        
        item_table = Table(item_data, colWidths=[1.5*inch, 1.5*inch])
        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(item_table)
        story.append(Spacer(1, 20))
    
    # Shaxs skorlari
    persons = data.get('persons', [])
    if persons:
        story.append(Paragraph("Shaxs Skorlari (EAP)", heading_style))
        
        # Faqat birinchi 10 ta shaxsni ko'rsatamiz
        display_persons = persons[:10]
        person_data = [["Shaxs", "EAP", "Standart Xato"]]
        for person in display_persons:
            person_data.append([
                f"Shaxs {person.get('person_index', 'N/A')}",
                f"{person.get('eap', 0):.3f}",
                f"{person.get('se', 0):.3f}"
            ])
        
        if len(persons) > 10:
            person_data.append([f"... va {len(persons) - 10} ta boshqa", "", ""])
        
        person_table = Table(person_data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch])
        person_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(person_table)
        story.append(Spacer(1, 20))
    
    # Grafiklar
    if items and persons:
        story.append(Paragraph("Vizual Tahlil", heading_style))
        
        # Item qiyinchilik grafigi
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Item qiyinchilik
        difficulties = [item.get('difficulty', 0) for item in items]
        item_ids = [item.get('item_id', f'Item{i+1}') for i, item in enumerate(items)]
        
        ax1.bar(range(len(difficulties)), difficulties, color='skyblue', alpha=0.7)
        ax1.set_xlabel('Itemlar')
        ax1.set_ylabel('Qiyinchilik')
        ax1.set_title('Item Qiyinchilik Darajasi')
        ax1.set_xticks(range(len(item_ids)))
        ax1.set_xticklabels(item_ids, rotation=45, ha='right')
        ax1.grid(True, alpha=0.3)
        
        # Shaxs skorlari taqsimoti
        eap_scores = [person.get('eap', 0) for person in persons if person.get('eap') is not None]
        if eap_scores:
            ax2.hist(eap_scores, bins=min(20, len(eap_scores)//2), color='lightgreen', alpha=0.7, edgecolor='black')
            ax2.set_xlabel('EAP Skor')
            ax2.set_ylabel('Chastota')
            ax2.set_title('Shaxs Skorlari Taqsimoti')
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Grafikni PDF ga qo'shish
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            plt.savefig(tmp_file.name, dpi=150, bbox_inches='tight')
            img = Image(tmp_file.name, width=6*inch, height=2.5*inch)
            story.append(img)
        
        plt.close()
    
    # PDF yaratish
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
