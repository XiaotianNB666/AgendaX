from PyQt5.QtWidgets import QWidget

def set_center(widget: QWidget, parent_widget: QWidget) -> None:
    container_size = parent_widget.size()
    widget_size = widget.size()

    x = (container_size.width() - widget_size.width()) // 2
    y = (container_size.height() - widget_size.height()) // 2

    widget.setGeometry(x, y, widget_size.width(), widget_size.height())