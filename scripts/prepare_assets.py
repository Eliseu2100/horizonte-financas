"""Gera o ícone Windows a partir do símbolo vetorial próprio do Elisei."""
from pathlib import Path
import struct
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QImage,QPainter
from PySide6.QtCore import QBuffer,QIODevice,Qt

def prepare():
    root=Path(__file__).resolve().parents[1];renderer=QSvgRenderer(str(root/'assets/elisei.svg'));images=[]
    for size in [16,24,32,48,64,128,256]:
        image=QImage(size,size,QImage.Format_ARGB32);image.fill(Qt.transparent);p=QPainter(image);renderer.render(p);p.end();buffer=QBuffer();buffer.open(QIODevice.WriteOnly);image.save(buffer,'PNG');images.append((size,bytes(buffer.data())))
    offset=6+16*len(images);header=struct.pack('<HHH',0,1,len(images));entries=b'';payload=b''
    for size,data in images:entries+=struct.pack('<BBBBHHII',size if size<256 else 0,size if size<256 else 0,0,0,1,32,len(data),offset);payload+=data;offset+=len(data)
    target=root/'src/elisei.ico';target.write_bytes(header+entries+payload);return target
if __name__=='__main__':print(prepare())
    
