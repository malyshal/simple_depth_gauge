import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QTableWidget,
                             QTableWidgetItem, QSplitter, QAbstractItemView)
from pyqtgraph.Qt import QtCore
from pyqtgraph.opengl import GLViewWidget, GLGridItem, GLMeshItem, GLLinePlotItem
import pyqtgraph as pg
import matplotlib.pyplot as plt
from pyqtgraph.opengl import MeshData
from scipy.interpolate import griddata

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('3D Surface Visualization')
        self.setGeometry(100, 100, 1200, 600)

        # Main Layout
        main_layout = QHBoxLayout()

        # Create a splitter to allow resizing of graph and table
        self.splitter = QSplitter(QtCore.Qt.Horizontal)

        # Create layout for graph and buttons
        graph_layout = QVBoxLayout()
        self.view = GLViewWidget()
        self.grid = GLGridItem()
        self.view.addItem(self.grid)
        self.view.setMinimumSize(500, 500)  # Set a minimum size for the graph

        # Buttons for graph and table
        button_layout = QHBoxLayout()
        self.generate_button = QPushButton('Generate')
        self.generate_button.clicked.connect(self.generate_data)
        button_layout.addWidget(self.generate_button)

        self.add_row_button = QPushButton('Add Row')
        self.add_row_button.clicked.connect(self.add_row)
        button_layout.addWidget(self.add_row_button)

        self.delete_row_button = QPushButton('Delete Row')
        self.delete_row_button.clicked.connect(self.delete_row)
        button_layout.addWidget(self.delete_row_button)

        graph_layout.addWidget(self.view)
        graph_layout.addLayout(button_layout)

        # Create table widget
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Angle', 'Length', 'Depth'])
        self.table.setRowCount(5)  # Initial row count
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)  # Select whole rows
        self.table.itemChanged.connect(self.update_surface)  # Connect table changes to update_surface

        # Add graph layout and table to splitter
        graph_widget = QWidget()
        graph_widget.setLayout(graph_layout)
        self.splitter.addWidget(graph_widget)
        self.splitter.addWidget(self.table)

        # Add splitter to main layout
        main_layout.addWidget(self.splitter)

        # Central Widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Save the initial camera parameters
        self.saved_camera_params = {
            'distance': 500,
            'azimuth': 60,
            'elevation': 30,
            'center': [0, 0, 0]  # Use list for center
        }

        # Initialize camera position and orientation
        # self.save_camera()
        # self.restore_camera()

        self.update_surface()

    def generate_data(self):
        angles = np.arange(0, 5 * 9, 9)
        lengths = np.linspace(0, 100, 19)  # Increased maximum length
        depths = np.random.uniform(0, 10, size=(5, 19))  # Decreased maximum depth

        self.table.setRowCount(len(angles) * len(lengths))
        for i, angle in enumerate(angles):
            for j, length in enumerate(lengths):
                depth = depths[i, j]  # No rounding
                self.table.setItem(i * len(lengths) + j, 0, QTableWidgetItem(f"{angle:.2f}"))
                self.table.setItem(i * len(lengths) + j, 1, QTableWidgetItem(f"{length:.2f}"))
                self.table.setItem(i * len(lengths) + j, 2, QTableWidgetItem(f"{depth:.2f}"))

        self.update_surface()

    def update_surface(self):
        # Save the current camera parameters
        self.save_camera()

        self.view.clear()
        self.grid = GLGridItem()
        self.view.addItem(self.grid)

        angles = []
        lengths = []
        depths = []

        row_count = self.table.rowCount()
        for i in range(row_count):
            angle_item = self.table.item(i, 0)
            length_item = self.table.item(i, 1)
            depth_item = self.table.item(i, 2)

            # Check if items are not None and have text
            if angle_item and length_item and depth_item:
                try:
                    angle = float(angle_item.text())
                    length = float(length_item.text())
                    depth = float(depth_item.text())
                    angles.append(angle)
                    lengths.append(length)
                    depths.append(depth)
                except ValueError:
                    continue  # Skip rows with invalid data

        angles = np.array(angles)
        lengths = np.array(lengths)
        depths = np.array(depths)

        if len(angles) == 0 or len(lengths) == 0:
            return  # No data to plot

        # Convert polar coordinates to Cartesian coordinates
        X = lengths * np.cos(np.deg2rad(angles))
        Y = lengths * np.sin(np.deg2rad(angles))
        Z = depths

        # Interpolation for smoother surface
        xi = np.linspace(min(X), max(X), 50)
        yi = np.linspace(min(Y), max(Y), 50)
        XI, YI = np.meshgrid(xi, yi)
        ZI = griddata((X, Y), Z, (XI, YI), method='cubic')

        # Create mesh data
        vertices = np.vstack([XI.flatten(), YI.flatten(), ZI.flatten()]).T

        # Create a list of faces (for simplicity, use a grid-based face construction)
        faces = []
        num_x = len(xi)
        num_y = len(yi)
        for i in range(num_y - 1):
            for j in range(num_x - 1):
                p1 = i * num_x + j
                p2 = p1 + 1
                p3 = p1 + num_x
                p4 = p3 + 1
                faces.append([p1, p2, p3])
                faces.append([p2, p4, p3])

        faces = np.array(faces)

        # Create MeshData and set vertex colors
        mesh_data = MeshData(vertexes=vertices, faces=faces)

        # Add color mapping based on Z values
        norm = plt.Normalize(vmin=np.min(Z), vmax=np.max(Z))
        color_map = plt.get_cmap('viridis')
        colors = color_map(norm(Z))[:, :3]  # Normalize and get RGB

        # Create face colors array with the same shape as faces
        face_colors = np.zeros((len(faces), 4))  # Create a color array for faces
        for idx, face in enumerate(faces):
            color_idx = idx % len(colors)  # Just an example, modify this for proper coloring
            face_colors[idx] = np.append(colors[color_idx], 1)  # Add alpha channel

        mesh_data.setFaceColors(face_colors)

        # Create the mesh item with smoothing enabled
        mesh = GLMeshItem(meshdata=mesh_data, smooth=True)  # Enable smoothing for a more realistic look
        self.view.addItem(mesh)

        # Draw coordinate axes
        self.draw_axes()

        # Restore saved camera parameters
        self.restore_camera()

        self.view.update()

    def draw_axes(self):
        # X-axis
        x_axis = GLLinePlotItem(pos=np.array([[0, 0, 0], [1, 0, 0]]), color=(1, 0, 0, 1), width=2)
        self.view.addItem(x_axis)

        # Y-axis
        y_axis = GLLinePlotItem(pos=np.array([[0, 0, 0], [0, 1, 0]]), color=(0, 1, 0, 1), width=2)
        self.view.addItem(y_axis)

        # Z-axis
        z_axis = GLLinePlotItem(pos=np.array([[0, 0, 0], [0, 0, 1]]), color=(0, 0, 1, 1), width=2)
        self.view.addItem(z_axis)

    def save_camera(self):
        # Save camera parameters as numerical values
        self.saved_camera_params = {
            'distance': self.view.opts.get('distance', 500),
            'azimuth': self.view.opts.get('azimuth', 60),
            'elevation': self.view.opts.get('elevation', 30),
            'center': self.view.opts.get('center', [0, 0, 0])  # Use list for center
        }

    def restore_camera(self):
        # Restore camera parameters from saved values
        if self.saved_camera_params:
            self.view.opts['distance'] = self.saved_camera_params.get('distance', 500)
            self.view.opts['azimuth'] = self.saved_camera_params.get('azimuth', 60)
            self.view.opts['elevation'] = self.saved_camera_params.get('elevation', 30)
            self.view.opts['center'] = self.saved_camera_params.get('center', [0, 0, 0])

    def add_row(self):
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        self.table.setItem(row_position, 0, QTableWidgetItem('0'))
        self.table.setItem(row_position, 1, QTableWidgetItem('0'))
        self.table.setItem(row_position, 2, QTableWidgetItem('0'))

    def delete_row(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())