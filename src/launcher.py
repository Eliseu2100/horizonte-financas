"""Entrada empacotada com log de falhas de inicialização."""
import os,sys,traceback
from pathlib import Path

def launch():
    try:
        from app import main
        main()
    except Exception:
        folder=Path(os.environ.get('HORIZONTE_DATA_DIR',str(Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'Horizonte')))
        folder.mkdir(parents=True,exist_ok=True);log=folder/'startup-error.txt';log.write_text(traceback.format_exc(),encoding='utf-8')
        if '--smoke-test' not in sys.argv:
            try:
                from PySide6.QtWidgets import QApplication,QMessageBox
                app=QApplication.instance() or QApplication(sys.argv);QMessageBox.critical(None,'Elisei: falha ao iniciar','Detalhes salvos em: '+str(log))
            except Exception:pass
        sys.exit(1)
if __name__=='__main__':launch()
    
