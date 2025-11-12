import base64
import time
from odoo import http
from odoo.http import request, Response


class PDFViewerController(http.Controller):

    @http.route('/ngsc/innovation/preview/info', type='http', auth='user')
    def view_active_pdf(self, **kwargs):
        record = request.env['ngsc_innovation.pdf_preview'].with_context(bin_size=False).sudo().search(
            [('active', '=', True)],
            limit=1
        )
        if not record or not record.pdf_file:
            return request.make_response(
                """
                <html>
                    <head>
                        <style>
                            body {
                                font-family: Arial, sans-serif;
                                display: flex;
                                justify-content: center;
                                align-items: center;
                                height: 100vh;
                                margin: 0;
                                background-color: #f4f4f9;
                            }
                            .container {
                                text-align: center;
                                padding: 40px;
                                background-color: #ffffff;
                                border-radius: 10px;
                                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                                max-width: 500px;
                            }
                            h2 {
                                color: #333;
                                font-size: 24px;
                                margin-bottom: 20px;
                            }
                            p {
                                color: #666;
                                font-size: 16px;
                                line-height: 1.5;
                            }
                            a {
                                display: inline-block;
                                margin-top: 20px;
                                padding: 10px 20px;
                                background-color: #007bff;
                                color: white;
                                text-decoration: none;
                                border-radius: 5px;
                                transition: background-color 0.3s;
                            }
                            a:hover {
                                background-color: #0056b3;
                            }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h2>Chưa có file giới thiệu về chương trình</h2>
                            <p>Vui lòng vào thiết lập để thêm file giới thiệu.</p>
                        </div>
                    </body>
                </html>
                """,
                headers=[('Content-Type', 'text/html')]
            )

        pdf_filename = record.pdf_filename or record.name or "document.pdf"

                
        pdf_data = base64.b64decode(record.pdf_file)
        chunk_size = 1024 * 1024  
        
        def stream_pdf():
            for i in range(0, len(pdf_data), chunk_size):
                yield pdf_data[i:i+chunk_size]
                
        return Response(
           stream_pdf(),
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'inline; filename="{pdf_filename}"'),
                ('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'),
                ('Pragma', 'no-cache')
            ]
        )