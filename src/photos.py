"""Enquadramento local de foto de perfil: recorte quadrado e visualização circular."""
from PySide6.QtCore import Qt,QRect,QRectF,Signal,QPointF
from PySide6.QtGui import QImage,QPixmap,QPainter,QPainterPath,QColor,QPen
from PySide6.QtWidgets import QWidget,QDialog,QVBoxLayout,QFormLayout,QSlider,QDialogButtonBox,QLabel

def circle_pixmap(image,size):
    pix=QPixmap(size,size);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing);path=QPainterPath();path.addEllipse(QRectF(1,1,size-2,size-2));p.setClipPath(path);side=min(image.width(),image.height());source=QRectF((image.width()-side)/2,(image.height()-side)/2,side,side);p.drawImage(QRectF(0,0,size,size),image,source);p.setClipping(False);p.setPen(QPen(QColor('#0065d4'),2));p.setBrush(Qt.NoBrush);p.drawEllipse(QRectF(1,1,size-2,size-2));p.end();return pix

class CropPreview(QWidget):
    moved=Signal(float,float)
    def __init__(self,image):
        super().__init__();self.image=image;self.zoom=1;self.x=0;self.y=0;self.anchor=None;self.setFixedSize(300,300);self.setAccessibleName('Prévia circular da foto');self.setCursor(Qt.OpenHandCursor)
    def source_rect(self):
        side=min(self.image.width(),self.image.height())/self.zoom;left=(self.image.width()-side)/2*(1+self.x);top=(self.image.height()-side)/2*(1+self.y);return QRect(round(left),round(top),round(side),round(side))
    def cropped(self):return self.image.copy(self.source_rect()).scaled(256,256,Qt.IgnoreAspectRatio,Qt.SmoothTransformation)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.drawPixmap(0,0,circle_pixmap(self.cropped(),300));p.end()
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:self.anchor=event.position();self.setCursor(Qt.ClosedHandCursor)
    def mouseMoveEvent(self,event):
        if self.anchor is None:return
        delta=event.position()-self.anchor;self.anchor=event.position();side=min(self.image.width(),self.image.height())/self.zoom
        self.x=max(-1,min(1,self.x-delta.x()*side/300*2/max(1,self.image.width()-side)));self.y=max(-1,min(1,self.y-delta.y()*side/300*2/max(1,self.image.height()-side)));self.moved.emit(self.x,self.y);self.update()
    def mouseReleaseEvent(self,event):self.anchor=None;self.setCursor(Qt.OpenHandCursor)

class PhotoCropDialog(QDialog):
    def __init__(self,image,parent=None):
        super().__init__(parent);self.setWindowTitle('Enquadrar foto de perfil');layout=QVBoxLayout(self);layout.addWidget(QLabel('Arraste a foto ou use os controles para ajustar o rosto na moldura.'));self.preview=CropPreview(image);layout.addWidget(self.preview,alignment=Qt.AlignCenter);form=QFormLayout();self.sliders={}
        for key,title,low,high,start in [('zoom','Zoom',100,400,100),('x','Horizontal',-100,100,0),('y','Vertical',-100,100,0)]:
            slider=QSlider(Qt.Horizontal);slider.setRange(low,high);slider.setValue(start);slider.setAccessibleName(title);self.sliders[key]=slider;slider.valueChanged.connect(self.update_preview);form.addRow(title,slider)
        layout.addLayout(form);self.preview.moved.connect(self.update_sliders);box=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);box.button(QDialogButtonBox.Save).setText('Usar enquadramento');box.button(QDialogButtonBox.Cancel).setText('Cancelar');box.accepted.connect(self.accept);box.rejected.connect(self.reject);layout.addWidget(box)
    def update_preview(self,*_):
        self.preview.zoom=self.sliders['zoom'].value()/100;self.preview.x=self.sliders['x'].value()/100;self.preview.y=self.sliders['y'].value()/100;self.preview.update()
    def update_sliders(self,x,y):
        for key,value in [('x',x),('y',y)]:self.sliders[key].blockSignals(True);self.sliders[key].setValue(round(value*100));self.sliders[key].blockSignals(False)
    
