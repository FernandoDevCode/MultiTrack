from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QGridLayout, QLabel, QVBoxLayout, QWidget

from stemlab.app import TARGET_LABELS, plan_for_targets
from stemlab.domain import CANONICAL_TARGETS, ConfirmedTargets


class InstrumentAnalysisPanel(QWidget):
    selection_changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._has_analysis = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Instrumentação sugerida")
        title.setStyleSheet("font-weight: 600;")
        layout.addWidget(title)
        explanation = QLabel("Sugestão automática — confirme ou corrija antes de separar.")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        grid = QGridLayout()
        grid.addWidget(QLabel("Instrumento"), 0, 0)
        grid.addWidget(QLabel("Evidência"), 0, 1)
        grid.addWidget(QLabel("Capacidade atual"), 0, 2)
        self.checkboxes: dict[str, QCheckBox] = {}
        self.evidence_labels: dict[str, QLabel] = {}
        self.capability_labels: dict[str, QLabel] = {}
        for row, target in enumerate(CANONICAL_TARGETS, start=1):
            checkbox = QCheckBox(TARGET_LABELS[target])
            evidence = QLabel("—")
            evidence.setWordWrap(True)
            capability = QLabel()
            capability.setWordWrap(True)
            checkbox.toggled.connect(self._selection_updated)
            self.checkboxes[target] = checkbox
            self.evidence_labels[target] = evidence
            self.capability_labels[target] = capability
            grid.addWidget(checkbox, row, 0)
            grid.addWidget(evidence, row, 1)
            grid.addWidget(capability, row, 2)
        layout.addLayout(grid)
        self.plan_summary = QLabel()
        self.plan_summary.setWordWrap(True)
        layout.addWidget(self.plan_summary)
        self._refresh_capabilities()

    @property
    def has_analysis(self) -> bool:
        return self._has_analysis

    def set_result(self, result: dict) -> None:
        evidence_by_target = {item["target_id"]: item for item in result["evidence"]}
        state_labels = {
            "suggested": "Sugerido",
            "possible": "Possível",
            "not_suggested": "Não sugerido",
        }
        for target in CANONICAL_TARGETS:
            item = evidence_by_target[target]
            checkbox = self.checkboxes[target]
            checkbox.blockSignals(True)
            checkbox.setChecked(item["state"] == "suggested")
            checkbox.blockSignals(False)
            self.evidence_labels[target].setText(state_labels[item["state"]])
        self._has_analysis = True
        self._refresh_capabilities()

    def clear(self) -> None:
        self._has_analysis = False
        for target in CANONICAL_TARGETS:
            self.checkboxes[target].blockSignals(True)
            self.checkboxes[target].setChecked(False)
            self.checkboxes[target].blockSignals(False)
            self.evidence_labels[target].setText("—")
        self._refresh_capabilities()

    def confirmed_targets(self) -> ConfirmedTargets:
        return ConfirmedTargets.from_iterable(
            target for target, checkbox in self.checkboxes.items() if checkbox.isChecked()
        )

    def current_plan(self):
        return plan_for_targets(self.confirmed_targets())

    def _selection_updated(self) -> None:
        self._refresh_capabilities()
        self.selection_changed.emit(self.confirmed_targets())

    def _refresh_capabilities(self) -> None:
        plan = self.current_plan()
        capabilities = {item.target_id: item for item in plan.capabilities}
        for target in CANONICAL_TARGETS:
            capability = capabilities.get(target)
            if capability is None:
                text = "Core Stems disponível" if target in {"vocals", "drums", "bass", "guitar", "piano"} else "Especialista indisponível"
            elif capability.status == "core_available":
                text = "Core Stems disponível"
            else:
                text = "Especialista indisponível"
            self.capability_labels[target].setText(text)
        unavailable = [
            TARGET_LABELS[item.target_id]
            for item in plan.capabilities
            if item.status == "specialist_unavailable"
        ]
        if not plan.confirmed_targets:
            summary = "Confirme ao menos um alvo para gerar o plano."
        elif plan.steps and unavailable:
            summary = "Core Stems será executado uma vez. Sem especialista: " + ", ".join(unavailable)
        elif plan.steps:
            summary = "Core Stems será executado uma vez para os alvos disponíveis."
        else:
            summary = "Os alvos confirmados ainda não possuem separador especializado."
        self.plan_summary.setText(summary)
