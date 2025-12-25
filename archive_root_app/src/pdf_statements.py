"""
Simple PDF generation for pay statements.
This is a minimal implementation - can be enhanced later.
"""
from datetime import date
from typing import List, Dict
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from io import BytesIO


def generate_pay_statement_pdf(
    auditor_name: str,
    pay_period: Dict,
    pay_items: List[Dict],
    output_path: str = None
) -> BytesIO:
    """
    Generate a PDF pay statement.
    
    Args:
        auditor_name: Name of the auditor
        pay_period: Pay period dict with start_date, end_date
        pay_items: List of pay item dicts
        output_path: Optional file path to save PDF
    
    Returns:
        BytesIO: PDF content as bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Container for the 'Flowable' objects
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    elements.append(Paragraph("Pay Statement", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Employee info
    info_data = [
        ["Employee:", auditor_name],
        ["Pay Period:", f"{pay_period.get('start_date', '')} to {pay_period.get('end_date', '')}"],
    ]
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Pay items table
    if pay_items:
        table_data = [["Date", "Hours", "Rate", "Amount"]]
        
        total_hours = 0
        total_amount = 0
        
        for item in pay_items:
            shift = item.get("shift") or {}
            check_in = shift.get("check_in", "")
            if check_in:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(check_in.replace("Z", "+00:00"))
                    date_str = dt.strftime("%Y-%m-%d")
                except:
                    date_str = str(check_in)[:10]
            else:
                date_str = "—"
            
            hours = float(item.get("hours", 0))
            rate = float(item.get("rate", 0))
            amount = float(item.get("amount", 0))
            
            total_hours += hours
            total_amount += amount
            
            table_data.append([
                date_str,
                f"{hours:.2f}",
                f"${rate:.2f}",
                f"${amount:.2f}"
            ])
        
        # Total row
        table_data.append([
            "TOTAL",
            f"{total_hours:.2f}",
            "",
            f"${total_amount:.2f}"
        ])
        
        table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No pay items for this period.", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Save to file if path provided
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(buffer.getvalue())
    
    return buffer


def generate_pay_period_summary_pdf(
    pay_period: Dict,
    all_pay_items: List[Dict],
    output_path: str = None
) -> BytesIO:
    """
    Generate a summary PDF for a pay period (all auditors).
    
    Args:
        pay_period: Pay period dict
        all_pay_items: List of all pay items for the period
        output_path: Optional file path to save PDF
    
    Returns:
        BytesIO: PDF content as bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    elements.append(Paragraph("Pay Period Summary", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Period info
    info_data = [
        ["Pay Period:", f"{pay_period.get('start_date', '')} to {pay_period.get('end_date', '')}"],
        ["Status:", pay_period.get('status', 'open').upper()],
    ]
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Group by auditor
    from collections import defaultdict
    by_auditor = defaultdict(list)
    for item in all_pay_items:
        auditor = item.get("auditor") or {}
        auditor_name = auditor.get("full_name", "Unknown")
        by_auditor[auditor_name].append(item)
    
    # Summary table
    table_data = [["Auditor", "Hours", "Amount"]]
    grand_total_hours = 0
    grand_total_amount = 0
    
    for auditor_name, items in sorted(by_auditor.items()):
        total_hours = sum(float(item.get("hours", 0)) for item in items)
        total_amount = sum(float(item.get("amount", 0)) for item in items)
        grand_total_hours += total_hours
        grand_total_amount += total_amount
        
        table_data.append([
            auditor_name,
            f"{total_hours:.2f}",
            f"${total_amount:.2f}"
        ])
    
    # Grand total
    table_data.append([
        "TOTAL",
        f"{grand_total_hours:.2f}",
        f"${grand_total_amount:.2f}"
    ])
    
    table = Table(table_data, colWidths=[4*inch, 1.5*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
    ]))
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(buffer.getvalue())
    
    return buffer

