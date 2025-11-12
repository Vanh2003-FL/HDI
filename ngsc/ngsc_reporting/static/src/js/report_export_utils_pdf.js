odoo.define('ngsc_reporting.ReportExportUtils', function (require) {
    'use strict';

    var ReportExportUtils = {
        exportElementToPDF: function (elementId, fileName) {
            const element = document.getElementById(elementId);
            const pdf = new jsPDF('l', 'mm', 'a4');
            const pageWidth = pdf.internal.pageSize.getWidth();
            const pageHeight = pdf.internal.pageSize.getHeight();
            const margin = 10;

            html2canvas(element, {
                scale: 1,
                scrollY: -window.scrollY,
                useCORS: true,
                allowTaint: true,
                logging: false,
                windowHeight: element.scrollHeight
            }).then(canvas => {
                const imgWidth = pageWidth - margin * 2;
                const pageImageRatio = imgWidth / canvas.width;
                const pageImageHeight = canvas.height * pageImageRatio;
                const pageHeightPx = (pageHeight - margin * 2) / pageImageRatio;

                const ctx = canvas.getContext('2d');
                let renderedHeight = 0;
                let pageCount = 0;

                while (renderedHeight < canvas.height) {
                    const canvasPage = document.createElement('canvas');
                    canvasPage.width = canvas.width;
                    canvasPage.height = Math.min(pageHeightPx, canvas.height - renderedHeight);

                    const ctxPage = canvasPage.getContext('2d');
                    ctxPage.putImageData(ctx.getImageData(0, renderedHeight, canvas.width, canvasPage.height), 0, 0);

                    const imgData = canvasPage.toDataURL('image/png');
                    if (pageCount > 0) pdf.addPage();

                    pdf.addImage(imgData, 'JPEG', margin, margin, imgWidth, canvasPage.height * pageImageRatio);

                    renderedHeight += canvasPage.height;
                    pageCount++;
                }

                pdf.save(fileName || 'export.pdf');
            });
        }
    };

    return ReportExportUtils;
});
