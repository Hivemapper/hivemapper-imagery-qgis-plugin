from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QListWidget

class MyImageryDialog(QDialog):
    def __init__(self, urls, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Imagery URLs")
        layout = QVBoxLayout()

        label = QLabel("Here are the fetched imagery URLs:")
        layout.addWidget(label)

        # Create a list widget to display the URLs
        url_list = QListWidget()
        for url in urls:
            url_list.addItem(url)

        layout.addWidget(url_list)

        self.setLayout(layout)
