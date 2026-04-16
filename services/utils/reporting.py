import pandas as pd
from fpdf import FPDF
import os
from datetime import datetime
from services.utils.config import logger


def generate_csv_report(cluster_data, output_dir, timestamp):
    """
    Generates a CSV file summarizing the analyzed clusters.

    :param cluster_data: List of dictionaries with cluster information.
    :param output_dir: Directory where the report will be saved.
    :param timestamp: Forecast timestamp.
    """
    if not cluster_data:
        logger.warning("No cluster data available to generate CSV report.")
        return None

    report_df = pd.DataFrame(cluster_data)

    # Rename columns for the end-user report
    report_df.rename(columns={
        'cluster_id': 'Cluster ID',
        'region': 'Region',
        'is_mature': 'Is Mature?',
        'n_trajectories': 'Total Trajectories',
        'dispersion_km': 'Initial Dispersion (km)',
        'estimated_date': 'Estimated Start/Impact Date'
    }, inplace=True)

    csv_path = os.path.join(output_dir, f'cluster_report_{timestamp}.csv')
    report_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    logger.info(f"CSV report successfully generated at: {csv_path}")

    return csv_path


class PDFReport(FPDF):
    def header(self):
        # self.image('path/to/logo.png', 10, 8, 33)
        self.set_font('helvetica', 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'Cluster Analysis Report - Hurakan', border=0, align='C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')


def generate_pdf_report(cluster_data, output_dir, timestamp, map_filename):
    """
    Generates an executive summary PDF report.
    """
    if not cluster_data:
        return None

    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)

    pdf.cell(0, 10, f"Model Timestamp: {timestamp}", ln=True)
    pdf.cell(0, 10, f"Interactive Map: {map_filename}", ln=True)
    pdf.ln(10)

    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, "Detected Clusters Summary:", ln=True)
    pdf.set_font("helvetica", size=11)

    # Simple table setup
    widths = [20, 30, 40, 35, 30]
    headers = ['ID', 'Region', 'Trajectories', 'Dispersion', 'Status']

    # Print headers
    pdf.set_fill_color(200, 220, 255)
    for i, col in enumerate(headers):
        pdf.cell(widths[i], 10, col, border=1, fill=True, align='C')
    pdf.ln()

    # Print data rows
    for row in cluster_data:
        status = "Mature" if row.get('is_mature') else "Forming"
        dispersion = row.get('dispersion_km', 'N/A')
        disp_str = f"{dispersion} km" if dispersion != 'N/A' else "N/A"

        pdf.cell(widths[0], 10, str(row.get('cluster_id', '')), border=1, align='C')
        pdf.cell(widths[1], 10, str(row.get('region', '')).capitalize(), border=1, align='C')
        pdf.cell(widths[2], 10, str(row.get('n_trajectories', '')), border=1, align='C')
        pdf.cell(widths[3], 10, disp_str, border=1, align='C')
        pdf.cell(widths[4], 10, status, border=1, align='C')
        pdf.ln()

    pdf_path = os.path.join(output_dir, f'executive_report_{timestamp}.pdf')
    pdf.output(pdf_path)
    logger.info(f"PDF report successfully generated at: {pdf_path}")

    return pdf_path