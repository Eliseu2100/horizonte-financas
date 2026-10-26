from pathlib import Path
import shutil
root = Path(__file__).resolve().parents[1]
target = root / 'dist' / 'Elisei' / 'licenses'
target.mkdir(parents=True, exist_ok=True)
for source in (root / 'licenses').glob('*.txt'):
    shutil.copy2(source, target / source.name)
shutil.copy2(root / 'THIRD_PARTY_NOTICES.txt', target / 'THIRD_PARTY_NOTICES.txt')
    
