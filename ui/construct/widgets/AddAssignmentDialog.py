from ui.construct.widgets.InlineDialogWidget import InlineDialogWidget


class AddAssignmentDialog(InlineDialogWidget):
    def __init__(self, parent=None):
        InlineDialogWidget.__init__(self, parent)
        self.setWindowTitle("添加作业")