from __future__ import annotations

import math
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Circle, Drawing, Line, Path as DrawingPath, String
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image as RLImage,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


NTT_BLUE = HexColor("#0072BC")
NTT_CYAN = HexColor("#00A7E1")
NTT_DARK = HexColor("#0B1F33")
NTT_DARK_ALT = HexColor("#132B44")
NTT_LIGHT = HexColor("#F4F7FA")
NTT_SUCCESS = HexColor("#198754")
NTT_WARNING = HexColor("#FFC107")
NTT_DANGER = HexColor("#DC3545")
NTT_MUTED = HexColor("#6C757D")
GRID = HexColor("#DCE5EC")


def _text(value) -> str:
    if value is None:
        return ""
    return (
        str(value)
        .replace("—", "-")
        .replace("–", "-")
        .replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("•", "-")
    )


def _p(value, style):
    raw = _text(value)
    tokens = {"<br/>": "__BR__", "<br>": "__BR__", "<b>": "__B_OPEN__", "</b>": "__B_CLOSE__"}
    for markup, token in tokens.items():
        raw = raw.replace(markup, token)
    safe = escape(raw).replace("\n", "<br/>")
    safe = safe.replace("__BR__", "<br/>").replace("__B_OPEN__", "<b>").replace("__B_CLOSE__", "</b>")
    return Paragraph(safe, style)


def _score(value) -> str:
    return "N/D" if value is None else f"{float(value):.2f}"


class _ReportDocTemplate(BaseDocTemplate):
    def __init__(self, filename, *, title: str, **kwargs):
        super().__init__(filename, title=title, **kwargs)
        self._bookmark_number = 0

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name in {"ReportH1", "ReportH2"}:
            level = 0 if flowable.style.name == "ReportH1" else 1
            key = getattr(flowable, "_bookmark_name", None)
            if key is None:
                self._bookmark_number += 1
                key = f"section-{self._bookmark_number}"
                flowable._bookmark_name = key
            text = flowable.getPlainText()
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=False)
            self.notify("TOCEntry", (level, text, self.page, key))


class ReportPdfService:
    def __init__(self) -> None:
        self.styles = self._styles()

    @staticmethod
    def _styles() -> dict:
        base = getSampleStyleSheet()
        return {
            "cover_kicker": ParagraphStyle("CoverKicker", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=NTT_CYAN, spaceAfter=8),
            "cover_title": ParagraphStyle("CoverTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=29, leading=33, textColor=colors.white, alignment=TA_LEFT, spaceAfter=14),
            "cover_subtitle": ParagraphStyle("CoverSubtitle", parent=base["Normal"], fontName="Helvetica", fontSize=14, leading=19, textColor=HexColor("#D8E8F2"), spaceAfter=10),
            "cover_meta": ParagraphStyle("CoverMeta", parent=base["Normal"], fontName="Helvetica", fontSize=9, leading=14, textColor=colors.white),
            "h1": ParagraphStyle("ReportH1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=NTT_DARK, spaceBefore=12, spaceAfter=10, keepWithNext=True),
            "h2": ParagraphStyle("ReportH2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=NTT_BLUE, spaceBefore=10, spaceAfter=7, keepWithNext=True),
            "body": ParagraphStyle("ReportBody", parent=base["BodyText"], fontName="Helvetica", fontSize=8.7, leading=12.5, textColor=NTT_DARK, spaceAfter=6),
            "small": ParagraphStyle("ReportSmall", parent=base["BodyText"], fontName="Helvetica", fontSize=7, leading=9, textColor=NTT_MUTED),
            "table": ParagraphStyle("ReportTable", parent=base["BodyText"], fontName="Helvetica", fontSize=6.8, leading=8.5, textColor=NTT_DARK),
            "table_bold": ParagraphStyle("ReportTableBold", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=6.8, leading=8.5, textColor=NTT_DARK),
            "metric_label": ParagraphStyle("MetricLabel", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=NTT_MUTED, alignment=TA_CENTER),
            "metric_value": ParagraphStyle("MetricValue", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=18, leading=21, textColor=NTT_BLUE, alignment=TA_CENTER),
            "toc_title": ParagraphStyle("TOCTitle", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=NTT_DARK, spaceAfter=15),
            "toc_l0": ParagraphStyle("TOC0", fontName="Helvetica-Bold", fontSize=9, leading=13, leftIndent=0, firstLineIndent=0, textColor=NTT_DARK, spaceBefore=5),
            "toc_l1": ParagraphStyle("TOC1", fontName="Helvetica", fontSize=8, leading=11, leftIndent=14, firstLineIndent=0, textColor=NTT_MUTED, spaceBefore=2),
        }

    def build(self, payload: dict) -> BytesIO:
        output = BytesIO()
        title = f"Assessment DevSecOps - {payload['assessment']['organization']}"
        branding = payload.get("branding", {})
        company_name = branding.get("company_name", "NTT DATA")
        classification = branding.get("classification", "Confidencial")
        document = _ReportDocTemplate(
            output,
            title=title,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=20 * mm,
            bottomMargin=18 * mm,
            author=f"{company_name} DevSecOps Assessment",
            subject="Reporte de madurez OWASP SAMM",
        )
        document.branding = {"company_name": company_name, "classification": classification}
        frame = Frame(document.leftMargin, document.bottomMargin, document.width, document.height, id="body-frame")
        cover_frame = Frame(0, 0, A4[0], A4[1], leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="cover-frame")
        document.addPageTemplates([
            PageTemplate(id="cover", frames=[cover_frame], onPage=self._cover_page),
            PageTemplate(id="body", frames=[frame], onPage=self._body_page),
        ])
        story = []
        story.extend(self._cover(payload))
        story.append(NextPageTemplate("body"))
        story.append(PageBreak())
        story.extend(self._toc())
        story.append(PageBreak())
        story.extend(self._executive(payload))
        story.extend(self._function_section(payload))
        story.extend(self._practice_section(payload))
        story.extend(self._gaps(payload))
        story.extend(self._recommendations(payload))
        story.extend(self._roadmap(payload))
        story.extend(self._evidence_appendix(payload))
        story.extend(self._observations(payload))
        story.extend(self._traceability(payload))
        document.multiBuild(story)
        output.seek(0)
        return output

    def _cover_page(self, canvas, doc) -> None:
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(NTT_DARK)
        canvas.rect(0, 0, width, height, stroke=0, fill=1)
        canvas.setFillColor(NTT_BLUE)
        canvas.rect(0, height - 16 * mm, width, 16 * mm, stroke=0, fill=1)
        canvas.setFillColor(NTT_CYAN)
        canvas.rect(0, 0, 12 * mm, height, stroke=0, fill=1)
        canvas.setStrokeColor(HexColor("#28455E"))
        for offset in range(0, 160, 20):
            canvas.line(width - 70 * mm + offset, 0, width, 70 * mm - offset)
        canvas.restoreState()

    def _body_page(self, canvas, doc) -> None:
        width, height = A4
        canvas.saveState()
        canvas.setStrokeColor(GRID)
        canvas.line(18 * mm, height - 13 * mm, width - 18 * mm, height - 13 * mm)
        canvas.setFont("Helvetica-Bold", 7)
        canvas.setFillColor(NTT_BLUE)
        canvas.drawString(18 * mm, height - 10 * mm, f"{doc.branding['company_name'].upper()} DEVSECOPS ASSESSMENT")
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(NTT_MUTED)
        canvas.drawRightString(width - 18 * mm, height - 10 * mm, "OWASP SAMM")
        canvas.setStrokeColor(GRID)
        canvas.line(18 * mm, 12 * mm, width - 18 * mm, 12 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(18 * mm, 8 * mm, f"{doc.branding['classification']} - uso autorizado")
        canvas.drawRightString(width - 18 * mm, 8 * mm, f"Página {doc.page}")
        canvas.restoreState()

    def _cover(self, payload: dict) -> list:
        assessment = payload["assessment"]
        result = payload["result"]
        data = [
            Spacer(1, 38 * mm),
            Table([[Spacer(1, 12 * mm)]], colWidths=[12 * mm], rowHeights=[12 * mm]),
        ]
        logo = self._cover_logo(payload)
        if logo is not None:
            data.append(logo)
            data.append(Spacer(1, 5 * mm))
        else:
            data.append(Spacer(1, 8 * mm))
        data.extend([
            Table(
                [[
                    _p(f"{payload.get('branding', {}).get('company_name', 'NTT DATA')} / APPSEC / OWASP SAMM", self.styles["cover_kicker"]),
                ]],
                colWidths=[158 * mm],
                style=TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 27 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 12 * mm)]),
            ),
            Table(
                [[_p("Reporte de madurez DevSecOps", self.styles["cover_title"])]],
                colWidths=[180 * mm],
                style=TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 27 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 12 * mm)]),
            ),
            Table(
                [[_p(assessment["organization"], self.styles["cover_subtitle"])],
                 [_p(assessment["name"], self.styles["cover_subtitle"])]],
                colWidths=[180 * mm],
                style=TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 27 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 12 * mm)]),
            ),
            Spacer(1, 17 * mm),
            Table(
                [[
                    _p(f"Madurez actual<br/><b>{_score(result['overall_score'])} / 3,00</b>", self.styles["cover_meta"]),
                    _p(f"Nivel objetivo<br/><b>{_score(result['target_score'])}</b>", self.styles["cover_meta"]),
                    _p(f"Avance<br/><b>{float(result['progress_percent']):.1f}%</b>", self.styles["cover_meta"]),
                ]],
                colWidths=[50 * mm, 50 * mm, 50 * mm],
                rowHeights=[22 * mm],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), NTT_DARK_ALT),
                    ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#3D5870")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#3D5870")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]),
                hAlign="CENTER",
            ),
            Spacer(1, 40 * mm),
            Table(
                [[_p(f"Versión SAMM: {assessment['questionnaire_version']}<br/>Fuente: {assessment['scoring_source']}<br/>Generado: {payload['generated_at']}", self.styles["cover_meta"])]],
                colWidths=[180 * mm],
                style=TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 27 * mm)]),
            ),
        ])
        return data

    def _cover_logo(self, payload: dict):
        logo_path = payload.get("branding", {}).get("logo_path", "")
        if not logo_path:
            return None
        candidate = Path(logo_path)
        if not candidate.is_file() or candidate.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            return None
        try:
            logo = RLImage(str(candidate))
            maximum_width = 42 * mm
            maximum_height = 14 * mm
            scale = min(maximum_width / logo.imageWidth, maximum_height / logo.imageHeight)
            logo.drawWidth = logo.imageWidth * scale
            logo.drawHeight = logo.imageHeight * scale
            return Table(
                [[logo]],
                colWidths=[180 * mm],
                style=TableStyle([
                    ("LEFTPADDING", (0, 0), (-1, -1), 27 * mm),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]),
            )
        except Exception:
            return None

    def _toc(self) -> list:
        toc = TableOfContents()
        toc.levelStyles = [self.styles["toc_l0"], self.styles["toc_l1"]]
        return [_p("Tabla de contenidos", self.styles["toc_title"]), toc]

    def _metric_cards(self, payload: dict) -> Table:
        result = payload["result"]
        summary = result["status_summary"]
        statuses = summary.get("statuses", {})
        metrics = [
            ("MADUREZ", _score(result["overall_score"])),
            ("OBJETIVO", _score(result["target_score"])),
            ("BRECHA", _score(result["gap"])),
            ("AVANCE", f"{float(result['progress_percent']):.1f}%"),
            ("APROBADAS", statuses.get("approved", 0)),
            ("PENDIENTES", summary.get("pending_for_source", 0)),
        ]
        cells = []
        for label, value in metrics:
            cells.append(Table([
                [_p(label, self.styles["metric_label"])],
                [_p(value, self.styles["metric_value"])],
            ], colWidths=[27 * mm], rowHeights=[7 * mm, 13 * mm], style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), NTT_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, GRID),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])))
        return Table([cells], colWidths=[29 * mm] * 6, hAlign="LEFT", style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

    def _executive(self, payload: dict) -> list:
        assessment = payload["assessment"]
        result = payload["result"]
        summary = result["status_summary"]
        return [
            _p("1. Resumen ejecutivo", self.styles["h1"]),
            self._metric_cards(payload),
            Spacer(1, 6 * mm),
            _p(
                f"El assessment de <b>{assessment['organization']}</b> obtiene una madurez general de "
                f"<b>{_score(result['overall_score'])}</b> sobre 3,00. El objetivo definido es "
                f"<b>{_score(result['target_score'])}</b>, con una brecha de <b>{_score(result['gap'])}</b>. "
                f"El avance operativo alcanza {float(result['progress_percent']):.1f}% y el cálculo utiliza "
                f"la fuente '{assessment['scoring_source']}'.",
                self.styles["body"],
            ),
            _p(
                f"Se evaluaron {summary.get('total_questions', 0)} preguntas, de las cuales "
                f"{summary.get('not_applicable_questions', 0)} fueron consideradas no aplicables. "
                f"Las preguntas pendientes se mantienen como cero y no se excluyen del cálculo, evitando "
                f"sobreestimar la postura de madurez.",
                self.styles["body"],
            ),
            _p("Alcance", self.styles["h2"]),
            _p(assessment.get("scope") or "No se registró un alcance específico.", self.styles["body"]),
            _p("Trazabilidad del cálculo", self.styles["h2"]),
            self._key_value_table([
                ("Versión SAMM", assessment["questionnaire_version"]),
                ("Snapshot", result["snapshot_number"] or "Vista previa"),
                ("Versión de fórmula", result["calculation_metadata"].get("calculation_version", "")),
                ("Hash de entrada", result["input_hash"]),
                ("Fecha de generación", payload["generated_at"]),
            ]),
        ]

    def _function_section(self, payload: dict) -> list:
        rows = [["Función", "Actual", "Objetivo", "Brecha", "Avance", "Pendientes"]]
        for item in payload["functions"]:
            rows.append([
                _p(item["name"], self.styles["table_bold"]),
                _score(item["score"]), _score(item["target_score"]), _score(item["gap"]),
                f"{float(item['normalized_percent']):.1f}%", str(item["pending_count"]),
            ])
        return [
            _p("2. Resultado por función", self.styles["h1"]),
            self._radar_chart(payload["functions"]),
            Spacer(1, 4 * mm),
            self._table(rows, [62 * mm, 21 * mm, 21 * mm, 20 * mm, 22 * mm, 20 * mm]),
        ]

    def _practice_section(self, payload: dict) -> list:
        rows = [["Función", "Práctica", "Actual", "Objetivo", "Brecha", "Pendientes"]]
        for item in payload["practices"]:
            rows.append([
                _p(item.get("metadata", {}).get("function_name", ""), self.styles["table"]),
                _p(item["name"], self.styles["table_bold"]),
                _score(item["score"]), _score(item["target_score"]), _score(item["gap"]), str(item["pending_count"]),
            ])
        return [
            _p("3. Resultado por práctica", self.styles["h1"]),
            self._practice_bars(payload["practices"]),
            Spacer(1, 4 * mm),
            self._table(rows, [35 * mm, 58 * mm, 19 * mm, 19 * mm, 19 * mm, 19 * mm]),
        ]

    def _gaps(self, payload: dict) -> list:
        streams = sorted(payload["streams"], key=lambda item: (-(item.get("gap") or 0), item["name"]))
        rows = [["Prioridad", "Función / Práctica", "Flujo", "Actual", "Objetivo", "Brecha"]]
        for item in streams:
            gap = float(item.get("gap") or 0)
            priority = "Crítica" if gap >= 1.5 else "Alta" if gap >= 1 else "Media" if gap >= 0.5 else "Baja"
            metadata = item.get("metadata", {})
            rows.append([
                priority,
                _p(f"{metadata.get('function_name', '')}<br/>{metadata.get('practice_name', '')}", self.styles["table"]),
                _p(item["name"], self.styles["table_bold"]),
                _score(item["score"]), _score(item["target_score"]), _score(item["gap"]),
            ])
        return [
            _p("4. Matriz de brechas", self.styles["h1"]),
            _p("La matriz ordena los flujos por brecha descendente para orientar la priorización del plan de mejora.", self.styles["body"]),
            self._table(rows, [21 * mm, 47 * mm, 55 * mm, 17 * mm, 18 * mm, 18 * mm], repeat_rows=1),
        ]

    def _recommendations(self, payload: dict) -> list:
        items = payload["recommendations"]
        story = [_p("5. Recomendaciones priorizadas", self.styles["h1"])]
        if not items:
            story.append(_p("No existen recomendaciones registradas para este assessment.", self.styles["body"]))
            return story
        rows = [["Prioridad", "Recomendación", "Riesgo", "Responsable", "Horizonte", "Estado"]]
        for item in items:
            rows.append([
                item["priority_label"],
                _p(f"<b>{escape(_text(item['title']))}</b><br/>{escape(_text(item['description']))}", self.styles["table"]),
                _p(item["risk"], self.styles["table"]),
                _p(item["owner"], self.styles["table"]),
                item["horizon"], item["status_label"],
            ])
        story.append(self._table(rows, [20 * mm, 58 * mm, 38 * mm, 25 * mm, 22 * mm, 20 * mm]))
        return story

    def _roadmap(self, payload: dict) -> list:
        story = [_p("6. Roadmap de mejora", self.styles["h1"])]
        for group in payload["roadmap"]:
            story.append(_p(group["horizon"], self.styles["h2"]))
            if not group["items"]:
                story.append(_p("Sin iniciativas asignadas a este horizonte.", self.styles["small"]))
                continue
            rows = [["Prioridad", "Iniciativa", "Responsable", "Esfuerzo", "Quick win", "Estado"]]
            for item in group["items"]:
                rows.append([
                    item["priority_label"], _p(item["title"], self.styles["table_bold"]),
                    _p(item["owner"], self.styles["table"]), item["effort"], "Sí" if item["quick_win"] else "No", item["status_label"],
                ])
            story.append(self._table(rows, [19 * mm, 69 * mm, 28 * mm, 21 * mm, 18 * mm, 24 * mm]))
        return story

    def _evidence_appendix(self, payload: dict) -> list:
        rows = [["Pregunta", "Archivo", "Tipo", "Tamaño", "Validación", "SHA-256"]]
        for item in payload["evidences"]:
            rows.append([
                item["question_code"], _p(item["filename"], self.styles["table"]), item["extension"].upper(),
                f"{item['size_bytes'] / 1024:.1f} KB", item["validation_status"], _p(item["sha256"], self.styles["small"]),
            ])
        return [
            PageBreak(),
            _p("7. Evidencias", self.styles["h1"]),
            _p(f"Se registraron {len(payload['evidences'])} evidencias activas. Los archivos no se incorporan al PDF; se documentan mediante metadatos y hash de integridad.", self.styles["body"]),
            self._table(rows, [19 * mm, 55 * mm, 15 * mm, 20 * mm, 22 * mm, 48 * mm]) if len(rows) > 1 else _p("No existen evidencias registradas.", self.styles["body"]),
        ]

    def _observations(self, payload: dict) -> list:
        rows = [["Pregunta", "Estado", "Observación", "Respuesta"]]
        for item in payload["observed_questions"]:
            rows.append([
                item["code"], item["status_label"], _p(item["reviewer_comment"], self.styles["table"]), _p(item["answer"], self.styles["table"]),
            ])
        return [
            _p("8. Preguntas observadas o rechazadas", self.styles["h1"]),
            self._table(rows, [22 * mm, 28 * mm, 77 * mm, 52 * mm]) if len(rows) > 1 else _p("No existen preguntas observadas o rechazadas.", self.styles["body"]),
        ]

    def _traceability(self, payload: dict) -> list:
        review_rows = [["Pregunta", "Versión", "Decisión", "Revisor", "Fecha", "Comentario"]]
        for item in payload["reviews"]:
            review_rows.append([
                item["question_code"], item["response_version"], item["decision"], item["reviewer"], item["reviewed_at"], _p(item["comment"], self.styles["table"]),
            ])
        audit_rows = [["Fecha", "Usuario", "Acción", "Entidad", "Resultado"]]
        for item in payload["audit_log"][:150]:
            audit_rows.append([item["occurred_at"], item["actor"], item["action"], item["entity_type"], item["result"]])
        story = [
            _p("9. Historial y bitácora", self.styles["h1"]),
            _p("Revisiones", self.styles["h2"]),
            self._table(review_rows, [22 * mm, 15 * mm, 24 * mm, 28 * mm, 33 * mm, 57 * mm]) if len(review_rows) > 1 else _p("No existen revisiones registradas.", self.styles["body"]),
            _p("Bitácora del assessment", self.styles["h2"]),
            self._table(audit_rows, [39 * mm, 37 * mm, 47 * mm, 35 * mm, 21 * mm]) if len(audit_rows) > 1 else _p("No existen eventos de auditoría asociados.", self.styles["body"]),
        ]
        return story

    def _key_value_table(self, entries: list[tuple[str, object]]) -> Table:
        rows = [[_p(label, self.styles["table_bold"]), _p(value, self.styles["table"])] for label, value in entries]
        return Table(rows, colWidths=[42 * mm, 137 * mm], style=TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), NTT_LIGHT),
            ("GRID", (0, 0), (-1, -1), 0.4, GRID),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))

    def _table(self, rows, widths, repeat_rows=1) -> Table:
        table = Table(rows, colWidths=widths, repeatRows=repeat_rows, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NTT_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("LEADING", (0, 0), (-1, 0), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, NTT_LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.35, GRID),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 6.8),
            ("LEADING", (0, 1), (-1, -1), 8.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return table

    def _radar_chart(self, functions: list[dict]) -> Drawing:
        width, height = 176 * mm, 83 * mm
        drawing = Drawing(width, height)
        center_x, center_y = 88 * mm, 39 * mm
        radius = 31 * mm
        count = max(len(functions), 3)
        for ring in range(1, 4):
            ring_radius = radius * ring / 3
            path = DrawingPath()
            for index in range(count):
                angle = math.pi / 2 + 2 * math.pi * index / count
                x = center_x + ring_radius * math.cos(angle)
                y = center_y + ring_radius * math.sin(angle)
                path.moveTo(x, y) if index == 0 else path.lineTo(x, y)
            path.closePath()
            path.strokeColor = GRID
            path.fillColor = None
            path.strokeWidth = 0.6
            drawing.add(path)
        score_path = DrawingPath()
        for index, item in enumerate(functions):
            angle = math.pi / 2 + 2 * math.pi * index / count
            score_radius = radius * min(max(float(item.get("score") or 0), 0), 3) / 3
            x = center_x + score_radius * math.cos(angle)
            y = center_y + score_radius * math.sin(angle)
            score_path.moveTo(x, y) if index == 0 else score_path.lineTo(x, y)
            drawing.add(Circle(x, y, 2.2, fillColor=NTT_BLUE, strokeColor=colors.white, strokeWidth=0.7))
            axis_x = center_x + radius * math.cos(angle)
            axis_y = center_y + radius * math.sin(angle)
            drawing.add(Line(center_x, center_y, axis_x, axis_y, strokeColor=GRID, strokeWidth=0.5))
            label_x = center_x + (radius + 10 * mm) * math.cos(angle)
            label_y = center_y + (radius + 8 * mm) * math.sin(angle)
            drawing.add(String(label_x, label_y, _text(item["name"])[:28], fontName="Helvetica", fontSize=6.5, fillColor=NTT_DARK, textAnchor="middle"))
        if functions:
            score_path.closePath()
            score_path.strokeColor = NTT_BLUE
            score_path.fillColor = HexColor("#CFEAF7")
            score_path.fillOpacity = 0.55
            score_path.strokeWidth = 1.6
            drawing.add(score_path)
        drawing.add(String(7 * mm, height - 8 * mm, "Madurez por función (0-3)", fontName="Helvetica-Bold", fontSize=8, fillColor=NTT_DARK))
        return drawing

    def _practice_bars(self, practices: list[dict]) -> Drawing:
        items = sorted(practices, key=lambda item: (-(item.get("gap") or 0), item["name"]))[:15]
        height = max(75 * mm, len(items) * 6 * mm)
        drawing = Drawing(176 * mm, height)
        chart = HorizontalBarChart()
        chart.x = 66 * mm
        chart.y = 10 * mm
        chart.width = 102 * mm
        chart.height = height - 18 * mm
        chart.data = [[float(item.get("score") or 0) for item in items]]
        chart.categoryAxis.categoryNames = [_text(item["name"])[:34] for item in items]
        chart.categoryAxis.labels.fontName = "Helvetica"
        chart.categoryAxis.labels.fontSize = 6.2
        chart.categoryAxis.labels.fillColor = NTT_DARK
        chart.categoryAxis.labels.boxAnchor = "e"
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = 3
        chart.valueAxis.valueStep = 0.5
        chart.valueAxis.labels.fontName = "Helvetica"
        chart.valueAxis.labels.fontSize = 6
        chart.valueAxis.gridStrokeColor = GRID
        chart.bars[0].fillColor = NTT_BLUE
        chart.bars[0].strokeColor = NTT_BLUE
        chart.barWidth = 3.2 * mm
        chart.barSpacing = 1.2 * mm
        drawing.add(chart)
        drawing.add(String(7 * mm, height - 6 * mm, "Prácticas con mayor brecha", fontName="Helvetica-Bold", fontSize=8, fillColor=NTT_DARK))
        return drawing


report_pdf_service = ReportPdfService()
