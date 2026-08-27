import io
import re
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from app import models

def strip_html_tags(text: str) -> str:
    """Removes HTML tags or converts basic tags for ReportLab Paragraph formatting."""
    if not text:
        return ""
    # Convert <br>, <p> to newlines or clean formatting
    text = re.sub(r'<br\s*/?>', '<br/>', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '<br/><br/>', text, flags=re.IGNORECASE)
    text = re.sub(r'<p[^>]*>', '', text, flags=re.IGNORECASE)
    # Strip any tags other than b, i, u, font, br
    allowed = ['b', 'i', 'u', 'font', 'br', 'strong', 'em']
    # Normalize strong -> b, em -> i
    text = re.sub(r'</?strong>', lambda m: '<b>' if '<strong>' in m.group() else '</b>', text)
    text = re.sub(r'</?em>', lambda m: '<i>' if '<em>' in m.group() else '</i>', text)
    # Strip all other unsupported tags
    text = re.sub(r'<(?!\/?(?:b|i|u|font|br)\b)[^>]+>', '', text)
    return text.strip()

def generate_memo_pdf(memo: models.Memo, organization: models.Organization) -> io.BytesIO:
    """
    Generates a formal institutional PDF for the given memo.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'OrgHeader',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=1  # Centered
    )
    
    sub_header_style = ParagraphStyle(
        'OrgSubHeader',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#4B5563'),
        alignment=1
    )
    
    doc_title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#111827'),
        alignment=1,
        spaceAfter=10
    )
    
    label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#374151')
    )
    
    val_style = ParagraphStyle(
        'MetaValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1F2937')
    )
    
    body_style = ParagraphStyle(
        'MemoBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=15,
        textColor=colors.HexColor('#111827'),
        spaceAfter=12
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1F2937')
    )

    elements = []

    # 1. Organization Header
    elements.append(Paragraph(organization.name.upper(), title_style))
    contact_parts = []
    if organization.contact_email:
        contact_parts.append(f"Email: {organization.contact_email}")
    if organization.contact_phone:
        contact_parts.append(f"Phone: {organization.contact_phone}")
    if organization.address:
        contact_parts.append(organization.address)
    
    if contact_parts:
        elements.append(Paragraph(" | ".join(contact_parts), sub_header_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=12))

    # 2. Document Title & Official Status Badge
    status_colors = {
        "Approved": colors.HexColor('#059669'),
        "Rejected": colors.HexColor('#DC2626'),
        "Pending Approval": colors.HexColor('#D97706'),
        "Pending Review": colors.HexColor('#2563EB'),
        "Changes Requested": colors.HexColor('#9333EA'),
        "Draft": colors.HexColor('#6B7280'),
    }
    status_bg = status_colors.get(memo.status, colors.HexColor('#4B5563'))
    
    status_text = memo.status.upper()
    elements.append(Paragraph("INTER-OFFICE MEMORANDUM", doc_title_style))
    
    # 3. Metadata Table
    dept_name = memo.department.name if memo.department else "General"
    cat_name = memo.category.name if memo.category else "Uncategorized"
    author_name = f"{memo.author.full_name} ({memo.author.designation or 'Staff'})" if memo.author else "Unknown"
    date_str = memo.submitted_at.strftime("%B %d, %Y %I:%M %p") if memo.submitted_at else memo.created_at.strftime("%B %d, %Y %I:%M %p")

    meta_data = [
        [
            Paragraph("Memo Reference:", label_style),
            Paragraph(f"<b>{memo.memo_number}</b>", val_style),
            Paragraph("Status:", label_style),
            Paragraph(f"<font color='{status_bg.hexval()}'><b>{status_text}</b></font>", val_style),
        ],
        [
            Paragraph("Date / Time:", label_style),
            Paragraph(date_str, val_style),
            Paragraph("Priority:", label_style),
            Paragraph(f"<b>{memo.priority}</b>", val_style),
        ],
        [
            Paragraph("From (Author):", label_style),
            Paragraph(author_name, val_style),
            Paragraph("Department:", label_style),
            Paragraph(dept_name, val_style),
        ],
        [
            Paragraph("Category:", label_style),
            Paragraph(cat_name, val_style),
            Paragraph("Final Approver:", label_style),
            Paragraph(memo.final_approver.full_name if memo.final_approver else "Pending", val_style),
        ],
        [
            Paragraph("Subject:", label_style),
            Paragraph(f"<b>{memo.title}</b>", val_style),
            Paragraph("", label_style),
            Paragraph("", val_style),
        ]
    ]

    t_meta = Table(meta_data, colWidths=[90, 180, 90, 180])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F9FAFB')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('SPAN', (1, 4), (3, 4)),  # Span Subject across row
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 14))

    # 4. Memo Content / Body
    elements.append(Paragraph("<b>MEMORANDUM CONTENT</b>", ParagraphStyle('SectionH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#1E3A8A'))))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#93C5FD'), spaceAfter=8))
    
    clean_body = strip_html_tags(memo.body)
    elements.append(Paragraph(clean_body, body_style))
    elements.append(Spacer(1, 10))

    # 5. Attachments Section
    if memo.attachments:
        elements.append(Paragraph("<b>ATTACHMENTS</b>", ParagraphStyle('SectionH2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#1E3A8A'))))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#93C5FD'), spaceAfter=6))
        
        att_rows = [[
            Paragraph("#", table_header_style),
            Paragraph("File Name", table_header_style),
            Paragraph("Size", table_header_style),
            Paragraph("Uploaded Date", table_header_style)
        ]]
        
        for idx, att in enumerate(memo.attachments, start=1):
            size_kb = f"{att.file_size / 1024:.1f} KB" if att.file_size < 1024*1024 else f"{att.file_size / (1024*1024):.2f} MB"
            att_rows.append([
                Paragraph(str(idx), table_cell_style),
                Paragraph(att.original_name, table_cell_style),
                Paragraph(size_kb, table_cell_style),
                Paragraph(att.created_at.strftime("%Y-%m-%d %H:%M"), table_cell_style)
            ])
            
        t_att = Table(att_rows, colWidths=[25, 275, 80, 160])
        t_att.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F9FAFB'), colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_att)
        elements.append(Spacer(1, 14))

    # 6. Sequential Workflow Approval History & Signatures
    elements.append(Paragraph("<b>WORKFLOW SEQUENCE & APPROVAL AUDIT TRAIL</b>", ParagraphStyle('SectionH3', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#1E3A8A'))))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#93C5FD'), spaceAfter=6))

    wf_rows = [[
        Paragraph("Step", table_header_style),
        Paragraph("Role / Participant", table_header_style),
        Paragraph("Action Taken", table_header_style),
        Paragraph("Timestamp", table_header_style),
        Paragraph("Comments / Feedback", table_header_style)
    ]]

    for step in sorted(memo.workflow_steps, key=lambda s: s.step_index):
        user_name = step.assigned_user.full_name if step.assigned_user else "Unassigned"
        role_label = f"{step.role_name}<br/><font color='#6B7280'>{user_name}</font>"
        
        action_label = step.action_taken or ("Pending Action" if step.is_current else "Upcoming")
        if step.on_behalf_of_user_id and step.action_by_user:
            action_label += f"<br/><font color='#6B7280'>via {step.action_by_user.full_name} (Delegate)</font>"
            
        time_label = step.action_timestamp.strftime("%Y-%m-%d %I:%M %p") if step.action_timestamp else "—"
        comment_label = step.comments or "—"

        wf_rows.append([
            Paragraph(f"#{step.step_index}", table_cell_style),
            Paragraph(role_label, table_cell_style),
            Paragraph(action_label.capitalize(), table_cell_style),
            Paragraph(time_label, table_cell_style),
            Paragraph(comment_label, table_cell_style)
        ])

    t_wf = Table(wf_rows, colWidths=[30, 140, 110, 110, 150])
    t_wf.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F9FAFB'), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_wf)
    elements.append(Spacer(1, 14))

    # 7. Document Security Footer
    elements.append(Spacer(1, 10))
    gen_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    footer_text = f"This document was digitally generated by the {organization.name} Inter-Office Memo Management System on {gen_time}. Verify authenticity with reference #{memo.memo_number}."
    elements.append(Paragraph(footer_text, ParagraphStyle('FooterNote', parent=styles['Normal'], fontName='Helvetica', fontSize=7, textColor=colors.HexColor('#9CA3AF'), alignment=1)))

    doc.build(elements)
    buffer.seek(0)
    return buffer
