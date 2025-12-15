#!/usr/bin/env python3
# JP Leftover Hunter v4.2 — MEGA ROBUST: Multi-class modular system
# =============================================================================
import os, re, chardet, traceback, sys, time, json, hashlib
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush, QTextCharFormat, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QThread, QCoreApplication, QMutex, QWaitCondition

# Optional DeepL
try:
    from deep_translator import GoogleTranslator as Translator
    DEEPL_AVAILABLE = True
except:
    DEEPL_AVAILABLE = False

# ============================================================================
# FILE PARSER - Handles file reading and dialog extraction
# ============================================================================
class FileParser:
    """Parse VN scenario files"""
    
    DIALOG_TAGS = re.compile(r'\[(r|np|cm|l|p|er|lr|resetfont|font|wait|quake|se|delay|nowait|rclick|image|layopt|trans|wt|wa|eval)\]')
    VAR_TAGS = re.compile(r'\[emb\s+exp=[^\]]+\]')
    JP_CHARS = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+')
    
    # Line pattern for different VN engines
    LINE_PATTERNS = [
        re.compile(r'^\s*(p|l|line|msg|dialog|mes)\d*\s*[:=]?\s*'),  # Common patterns
        re.compile(r'^\s*\[(p|l|line|msg|dialog|mes)\d*\]'),         # Bracket patterns
        re.compile(r'^\s*//\s*(p|l|line|msg|dialog|mes)\d*\s*[:=]?\s*'),  # Comment patterns
    ]
    
    CODE_PATTERNS = [
        re.compile(r'^\s*[@#\*;]'),
        re.compile(r'^\s*\[(?!r\]|np\]|cm\]|l\]|p\]|er\]|lr\])'),
        re.compile(r'^\s*\w+\s*='),
        re.compile(r'^\s*[\{\}]$'),
        re.compile(r'^\s*(if|elsif|else|endif|macro|endmacro|call|jump|return|iscript|endscript)'),
        re.compile(r'^\s*kag\.'),
        re.compile(r'^\s*//'),
        re.compile(r'^\s*(function|var)\s'),
    ]
    
    @staticmethod
    def detect_encoding(data: bytes) -> str:
        try:
            result = chardet.detect(data[:8192])
            enc = result['encoding'] or 'utf-8'
            return 'cp932' if 'shift' in enc.lower() else enc
        except:
            return 'utf-8'
    
    def is_code_line(self, line: str) -> bool:
        stripped = line.strip()
        if not stripped or len(stripped) < 2:
            return True
        return any(p.match(line) for p in self.CODE_PATTERNS)
    
    def extract_line_id(self, line: str) -> Optional[str]:
        """Extract line ID from various patterns"""
        for pattern in self.LINE_PATTERNS:
            match = pattern.search(line)
            if match:
                return match.group(1)
        return None
    
    def extract_text(self, line: str) -> str:
        """Extract clean dialog text"""
        # Remove variable tags
        line = self.VAR_TAGS.sub('', line)
        # Remove dialog tags
        line = self.DIALOG_TAGS.sub('', line)
        # Remove quotes
        line = re.sub(r'[「」『』""]', '', line)
        # Clean whitespace
        text = line.strip()
        return text
    
    def read_dialogs(self, filepath: str) -> Dict[str, Tuple[int, str]]:
        """Read file and extract dialog lines with line IDs"""
        dialogs = {}
        try:
            with open(filepath, 'rb') as f:
                raw = f.read()
            enc = self.detect_encoding(raw)
            content = raw.decode(enc, errors='ignore')
            
            # Track line IDs
            current_line_id = None
            line_counter = 0
            
            for ln, line in enumerate(content.splitlines(), 1):
                line_counter += 1
                
                # Check for line ID patterns
                line_id = self.extract_line_id(line)
                if line_id:
                    current_line_id = f"{line_id}{line_counter}"
                
                if self.is_code_line(line):
                    continue
                
                text = self.extract_text(line)
                if not text or len(text) < 2:
                    continue
                
                # Must have JP or English
                if self.JP_CHARS.search(text) or re.search(r'[a-zA-Z]', text):
                    # Use line ID if available, otherwise use line number
                    dialog_id = current_line_id if current_line_id else str(ln)
                    dialogs[dialog_id] = (ln, text)
        except Exception as e:
            print(f"Error: {filepath}: {str(e)[:50]}")
        
        return dialogs

# ============================================================================
# ANALYZER - Smart analysis logic
# ============================================================================
class DialogAnalyzer:
    """Analyze translation quality"""
    
    JP_CHARS = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+')
    
    PRONOUN_MAP = {
        'he': ['彼', '彼女'],
        'she': ['彼', '彼女'],
        'his': ['彼の', '彼女の'],
        'her': ['彼の', '彼女の'],
    }
    
    FORMAL_WORDS = [
        'therefore', 'thus', 'consequently', 'furthermore', 'moreover',
        'nevertheless', 'henceforth', 'wherein', 'hereby', 'whilst'
    ]
    
    def __init__(self, lang: str):
        self.lang = lang
        self.deepl_cache = {}
        self.cache_file = os.path.join(os.path.expanduser("~"), ".jlh_deepl_cache.json")
        self.load_cache()
    
    def load_cache(self):
        """Load DeepL cache from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.deepl_cache = json.load(f)
        except:
            self.deepl_cache = {}
    
    def save_cache(self):
        """Save DeepL cache to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.deepl_cache, f, ensure_ascii=False)
        except:
            pass
    
    def find_jp_chars(self, text: str) -> List[Tuple[str, int, int]]:
        """Find JP characters with positions"""
        return [(m.group(), m.start(), m.end()) for m in self.JP_CHARS.finditer(text)]
    
    def check_pronouns(self, jp: str, mtl: str) -> List[str]:
        """Check pronoun issues"""
        issues = []
        mtl_lower = mtl.lower()
        
        for pronoun, jp_words in self.PRONOUN_MAP.items():
            if pronoun not in mtl_lower:
                continue
            
            for jp_word in jp_words:
                if jp_word not in jp:
                    continue
                
                if pronoun in ['he', 'his'] and '彼女' in jp:
                    issues.append(f"'{pronoun}' wrong (彼女=she)")
                elif pronoun in ['she', 'her'] and '彼女' not in jp and '彼' in jp:
                    issues.append(f"'{pronoun}' wrong (彼=he)")
        
        return issues
    
    def check_anomalies(self, text: str) -> List[str]:
        """Check for misplaced symbols"""
        return re.findall(r'(?<!\[)[\]\[](?!\w+\])|["\u201c\u201d\u201e]{3,}|[。、]{2,}', text)
    
    def check_formal(self, text: str) -> List[str]:
        """Check for too formal words"""
        text_lower = text.lower()
        return [w for w in self.FORMAL_WORDS if w in text_lower]
    
    def get_deepl(self, jp: str) -> Optional[str]:
        """Get DeepL translation with caching"""
        if not DEEPL_AVAILABLE:
            return None
        
        # Create a hash key for the Japanese text
        text_hash = hashlib.md5(jp.encode('utf-8')).hexdigest()
        
        if text_hash in self.deepl_cache:
            return self.deepl_cache[text_hash]
        
        try:
            result = Translator(source='ja', target=self.lang).translate(jp)
            if result:
                # Make casual
                result = result.replace('Therefore', 'So').replace('Thus', 'So')
                result = result.replace('However', 'But').replace('Furthermore', 'Also')
                
                # Cache the result
                self.deepl_cache[text_hash] = result
                
                # Save cache periodically
                if len(self.deepl_cache) % 10 == 0:
                    self.save_cache()
                
            return result
        except:
            return None
    
    def analyze(self, jp: str, mtl: str) -> Dict:
        """Full analysis"""
        result = {
            'issue': None,
            'suggestion': '',
            'severity': 0,
            'highlights': []
        }
        
        # Check 1: Empty
        if not mtl or not mtl.strip():
            result['issue'] = 'Not translated'
            result['severity'] = 3
            deepl = self.get_deepl(jp)
            result['suggestion'] = deepl if deepl else ''
            return result
        
        # Check 2: JP chars
        jp_chars = self.find_jp_chars(mtl)
        if jp_chars:
            result['issue'] = f'JP chars: {len(jp_chars)} found'
            result['severity'] = 3
            for char, start, end in jp_chars:
                result['highlights'].append((char, start, end, '#ff0000'))
            deepl = self.get_deepl(jp)
            result['suggestion'] = deepl if deepl else ''
            return result
        
        # Check 3: Pronouns
        pronoun_issues = self.check_pronouns(jp, mtl)
        if pronoun_issues:
            result['issue'] = 'Pronoun: ' + '; '.join(pronoun_issues)
            result['severity'] = 2
            for issue in pronoun_issues:
                pronoun = issue.split("'")[1] if "'" in issue else ''
                if pronoun:
                    idx = mtl.lower().find(pronoun)
                    if idx >= 0:
                        result['highlights'].append((pronoun, idx, idx+len(pronoun), '#ffaa00'))
            deepl = self.get_deepl(jp)
            result['suggestion'] = deepl if deepl else ''
            return result
        
        # Check 4: Anomalies
        anomalies = self.check_anomalies(mtl)
        if anomalies:
            result['issue'] = f'Anomaly: {", ".join(set(anomalies))}'
            result['severity'] = 2
            for anom in set(anomalies):
                idx = mtl.find(anom)
                if idx >= 0:
                    result['highlights'].append((anom, idx, idx+len(anom), '#ff6600'))
            result['suggestion'] = 'Fix symbols'
            return result
        
        # Check 5: Formal
        formal = self.check_formal(mtl)
        if formal:
            result['issue'] = 'Too formal'
            result['severity'] = 1
            for word in formal:
                idx = mtl.lower().find(word)
                if idx >= 0:
                    result['highlights'].append((mtl[idx:idx+len(word)], idx, idx+len(word), '#00aaff'))
            deepl = self.get_deepl(jp)
            result['suggestion'] = deepl if deepl else 'Use casual language'
            return result
        
        # All OK
        result['issue'] = 'OK'
        result['severity'] = 0
        return result

# ============================================================================
# WORKER - Background processing
# ============================================================================
class QAWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    batch = pyqtSignal(list)
    
    def __init__(self, jp_folder: str, mtl_folder: str, lang: str):
        super().__init__()
        self.jp_folder = jp_folder
        self.mtl_folder = mtl_folder
        self.lang = lang
        self._running = True
        self.BATCH_SIZE = 50
        self.mutex = QMutex()
        self.condition = QWaitCondition()
    
    def run(self):
        try:
            if not DEEPL_AVAILABLE:
                self.log.emit("[WARN] DeepL unavailable - offline mode")
            
            parser = FileParser()
            analyzer = DialogAnalyzer(self.lang)
            
            # Find files
            jp_files = {}
            for root, _, files in os.walk(self.jp_folder):
                for f in files:
                    if f.lower().endswith(('.ks', '.tjs', '.txt', '.ks.scn', '.txt.scn')):
                        rel = os.path.relpath(os.path.join(root, f), self.jp_folder)
                        jp_files[rel] = os.path.join(root, f)
            
            if not jp_files:
                self.log.emit("[ERROR] No JP files found")
                self.finished.emit()
                return
            
            self.log.emit(f"[INFO] Found {len(jp_files)} files")
            
            total = len(jp_files)
            buffer = []
            issues = 0
            
            # Process files in parallel
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                
                for rel_path, jp_path in jp_files.items():
                    if not self._running:
                        break
                    
                    mtl_path = os.path.join(self.mtl_folder, rel_path)
                    if not os.path.exists(mtl_path):
                        self.log.emit(f"[WARN] MTL not found: {rel_path}")
                        continue
                    
                    # Submit file processing task
                    future = executor.submit(self.process_file, parser, analyzer, rel_path, jp_path, mtl_path)
                    futures.append((rel_path, future))
                
                # Process results as they complete
                for idx, (rel_path, future) in enumerate(futures):
                    if not self._running:
                        break
                    
                    try:
                        file_issues = future.result()
                        self.log.emit(f"[DEBUG] {rel_path}: {len(file_issues)} issues")
                        
                        for issue in file_issues:
                            buffer.append(issue)
                            issues += 1
                            
                            if len(buffer) >= self.BATCH_SIZE:
                                self.batch.emit(buffer)
                                buffer = []
                                QCoreApplication.processEvents()
                        
                        self.progress.emit(int((idx + 1) / len(futures) * 100))
                    except Exception as e:
                        self.log.emit(f"[ERROR] Processing {rel_path}: {str(e)}")
            
            if buffer:
                self.batch.emit(buffer)
            
            # Save DeepL cache
            analyzer.save_cache()
            
            self.log.emit(f"[DONE] Found {issues} issues")
            
        except Exception as e:
            self.log.emit(f"[FATAL] {str(e)}")
            traceback.print_exc()
        finally:
            self.finished.emit()
    
    def process_file(self, parser, analyzer, rel_path, jp_path, mtl_path):
        """Process a single file and return issues"""
        file_issues = []
        
        # Read files
        jp_dialogs = parser.read_dialogs(jp_path)
        mtl_dialogs = parser.read_dialogs(mtl_path)
        
        # Match dialogs by content similarity if line IDs don't match
        matched_dialogs = self.match_dialogs(jp_dialogs, mtl_dialogs)
        
        for dialog_id, (jp_line, jp_text, mtl_line, mtl_text) in matched_dialogs.items():
            if not jp_text:
                continue
            
            # Analyze
            analysis = analyzer.analyze(jp_text, mtl_text)
            
            # Only add issues
            if analysis['severity'] > 0:
                file_issues.append({
                    'file': rel_path,
                    'line': jp_line,
                    'mtl_line': mtl_line,
                    'jp_text': jp_text,
                    'mtl_text': mtl_text,
                    'issue': analysis['issue'],
                    'suggestion': analysis['suggestion'],
                    'severity': analysis['severity'],
                    'highlights': analysis['highlights']
                })
        
        return file_issues
    
    def match_dialogs(self, jp_dialogs, mtl_dialogs):
        """Match dialogs between JP and MTL files"""
        matched = {}
        
        # First, try direct matching by dialog ID
        for dialog_id, (jp_line, jp_text) in jp_dialogs.items():
            if dialog_id in mtl_dialogs:
                mtl_line, mtl_text = mtl_dialogs[dialog_id]
                matched[dialog_id] = (jp_line, jp_text, mtl_line, mtl_text)
        
        # Then, try content similarity matching for unmatched dialogs
        unmatched_jp = {k: v for k, v in jp_dialogs.items() if k not in matched}
        unmatched_mtl = {k: v for k, v in mtl_dialogs.items() if k not in matched}
        
        for jp_id, (jp_line, jp_text) in unmatched_jp.items():
            best_match = None
            best_score = 0
            
            for mtl_id, (mtl_line, mtl_text) in unmatched_mtl.items():
                # Simple similarity score based on length ratio
                if len(jp_text) > 0 and len(mtl_text) > 0:
                    length_ratio = min(len(jp_text), len(mtl_text)) / max(len(jp_text), len(mtl_text))
                    
                    # Check for common patterns that might indicate a match
                    jp_chars = DialogAnalyzer.JP_CHARS.findall(jp_text)
                    mtl_jp_chars = DialogAnalyzer.JP_CHARS.findall(mtl_text)
                    
                    # If MTL has JP chars, it's likely a bad translation, not a match
                    if mtl_jp_chars:
                        continue
                    
                    # If JP has no JP chars, it might be a code line, skip
                    if not jp_chars:
                        continue
                    
                    # Calculate similarity score
                    score = length_ratio
                    
                    if score > best_score:
                        best_score = score
                        best_match = (mtl_id, mtl_line, mtl_text)
            
            if best_match and best_score > 0.3:  # Threshold for matching
                mtl_id, mtl_line, mtl_text = best_match
                matched[jp_id] = (jp_line, jp_text, mtl_line, mtl_text)
                # Remove from unmatched MTL to avoid reusing
                if mtl_id in unmatched_mtl:
                    del unmatched_mtl[mtl_id]
        
        return matched
    
    def stop(self):
        self._running = False

# ============================================================================
# GUI - Main window
# ============================================================================
class MainWin(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JP Leftover Hunter v4.2 — MEGA")
        self.setMinimumSize(1600, 900)
        self.rows = []
        self.build_ui()
        self.apply_theme()
    
    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)
        
        # Folders
        fg = QGroupBox("Folders")
        fl = QVBoxLayout()
        fl.setSpacing(3)
        
        h1 = QHBoxLayout()
        h1.setSpacing(4)
        self.jp_le = QLineEdit()
        self.jp_le.setPlaceholderText("JP folder...")
        bj = QPushButton("📁")
        bj.setFixedSize(28, 28)
        bj.clicked.connect(lambda: self.browse(self.jp_le))
        h1.addWidget(QLabel("JP:"))
        h1.addWidget(self.jp_le, 1)
        h1.addWidget(bj)
        fl.addLayout(h1)
        
        h2 = QHBoxLayout()
        h2.setSpacing(4)
        self.mtl_le = QLineEdit()
        self.mtl_le.setPlaceholderText("MTL folder...")
        bm = QPushButton("📁")
        bm.setFixedSize(28, 28)
        bm.clicked.connect(lambda: self.browse(self.mtl_le))
        h2.addWidget(QLabel("MTL:"))
        h2.addWidget(self.mtl_le, 1)
        h2.addWidget(bm)
        fl.addLayout(h2)
        
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("Lang:"))
        self.lang_cb = QComboBox()
        self.lang_cb.addItems(["English (en)", "Indonesia (id)"])
        h3.addWidget(self.lang_cb)
        h3.addStretch()
        fl.addLayout(h3)
        
        fg.setLayout(fl)
        lay.addWidget(fg)
        
        # Buttons
        hb = QHBoxLayout()
        hb.setSpacing(4)
        
        self.btn_scan = QPushButton("🔍")
        self.btn_scan.setFixedSize(30, 30)
        self.btn_scan.clicked.connect(self.scan)
        
        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setFixedSize(30, 30)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(lambda: self.worker.stop() if hasattr(self, 'worker') else None)
        
        be = QPushButton("💾")
        be.setFixedSize(30, 30)
        be.clicked.connect(self.export)
        
        hb.addWidget(self.btn_scan)
        hb.addWidget(self.btn_stop)
        hb.addWidget(be)
        hb.addSpacing(8)
        
        hb.addWidget(QLabel("Filter:"))
        self.filter_cb = QComboBox()
        self.filter_cb.addItems(["All", "Not translated", "JP chars", "Pronoun", "Anomaly", "Too formal"])
        self.filter_cb.currentTextChanged.connect(self.apply_filter)
        hb.addWidget(self.filter_cb)
        hb.addStretch()
        
        self.stats = QLabel("Total: 0")
        hb.addWidget(self.stats)
        lay.addLayout(hb)
        
        # Table
        self.model = QStandardItemModel(0, 7)
        self.model.setHorizontalHeaderLabels(["File", "JP Line", "MTL Line", "Issue", "JP", "MTL", "Suggestion"])
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setColumnWidth(0, 140)
        self.table.setColumnWidth(1, 50)
        self.table.setColumnWidth(2, 50)
        self.table.setColumnWidth(3, 160)
        self.table.setColumnWidth(4, 320)
        self.table.setColumnWidth(5, 320)
        self.table.setColumnWidth(6, 350)
        lay.addWidget(self.table, 10)
        
        # Log
        self.log_te = QTextEdit()
        self.log_te.setReadOnly(True)
        self.log_te.setMaximumHeight(60)
        lay.addWidget(self.log_te)
        
        # Progress
        self.pbar = QProgressBar()
        self.pbar.setMaximumHeight(18)
        lay.addWidget(self.pbar)
    
    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow,QWidget{background:#000;color:#fff;font-family:'Segoe UI';font-size:9pt;}
            QLineEdit,QComboBox{background:#0a0a0a;border:1px solid#333;color:#fff;padding:4px;}
            QPushButton{background:#036;border:none;padding:4px;color:#fff;font-weight:bold;border-radius:3px;}
            QPushButton:hover{background:#048;}
            QPushButton:disabled{background:#333;color:#666;}
            QTableView{background:#000;alternate-background-color:#0a0a0a;gridline-color:#111;selection-background-color:#036;}
            QHeaderView::section{background:#0a0a0a;color:#fff;padding:5px;border:1px solid#222;font-weight:bold;}
            QGroupBox{border:1px solid#333;border-radius:3px;margin-top:6px;padding-top:6px;color:#0af;font-weight:bold;}
            QTextEdit{background:#000;color:#0f0;font-family:Consolas;font-size:8pt;}
            QProgressBar{background:#0a0a0a;border:1px solid#222;text-align:center;color:#fff;}
            QProgressBar::chunk{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #06c,stop:1 #0af);}
        """)
    
    def browse(self, le):
        d = QFileDialog.getExistingDirectory(self, "Select")
        if d:
            le.setText(d)
    
    def log(self, txt):
        self.log_te.append(txt)
    
    def scan(self):
        jp = self.jp_le.text()
        mtl = self.mtl_le.text()
        
        if not os.path.isdir(jp) or not os.path.isdir(mtl):
            QMessageBox.warning(self, "Error", "Invalid folders")
            return
        
        self.log_te.clear()
        self.model.removeRows(0, self.model.rowCount())
        self.rows.clear()
        self.pbar.setValue(0)
        self.log("[INFO] Starting...")
        
        self.btn_scan.setEnabled(False)
        self.btn_stop.setEnabled(True)
        
        self.thread = QThread()
        self.worker = QAWorker(jp, mtl, self.lang_cb.currentText().split()[-1][1:-1])
        self.worker.moveToThread(self.thread)
        
        self.thread.started.connect(self.worker.run)
        self.worker.batch.connect(self.add_batch)
        self.worker.progress.connect(self.pbar.setValue)
        self.worker.log.connect(self.log)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.scan_done)
        self.thread.start()
    
    def add_batch(self, batch):
        colors = {3: '#f44', 2: '#fa0', 1: '#0af', 0: '#0f0'}
        
        for r in batch:
            self.rows.append(r)
            row = []
            
            # File
            it = QStandardItem(r['file'])
            it.setEditable(False)
            it.setToolTip(r['file'])
            row.append(it)
            
            # JP Line
            it = QStandardItem(str(r['line']))
            it.setEditable(False)
            row.append(it)
            
            # MTL Line
            it = QStandardItem(str(r.get('mtl_line', r['line'])))
            it.setEditable(False)
            row.append(it)
            
            # Issue
            it = QStandardItem(r['issue'])
            it.setForeground(QColor(colors[r['severity']]))
            it.setEditable(False)
            row.append(it)
            
            # JP
            it = QStandardItem(r['jp_text'][:200])
            it.setEditable(False)
            it.setToolTip(r['jp_text'])
            row.append(it)
            
            # MTL with highlight info
            mtl = r['mtl_text'] if r['mtl_text'] else '[empty]'
            it = QStandardItem(mtl[:200])
            it.setEditable(False)
            
            # Add highlight info to tooltip
            if r['highlights']:
                hl_text = ', '.join([f"'{h[0]}'" for h in r['highlights']])
                it.setToolTip(f"{mtl}\n\n🔴 HIGHLIGHTED: {hl_text}")
                # Color background
                it.setBackground(QBrush(QColor(colors[r['severity']]).darker(300)))
            else:
                it.setToolTip(mtl)
            row.append(it)
            
            # Suggestion
            sug = r['suggestion'][:200] if r['suggestion'] else ''
            it = QStandardItem(sug)
            it.setEditable(False)
            it.setToolTip(r['suggestion'])
            row.append(it)
            
            self.model.appendRow(row)
        
        # Update stats
        total = len(self.rows)
        s3 = sum(1 for r in self.rows if r['severity'] == 3)
        s2 = sum(1 for r in self.rows if r['severity'] == 2)
        s1 = sum(1 for r in self.rows if r['severity'] == 1)
        self.stats.setText(
            f"Total: {total} | "
            f"<span style='color:#f44'>Critical: {s3}</span> | "
            f"<span style='color:#fa0'>Warning: {s2}</span> | "
            f"<span style='color:#0af'>Info: {s1}</span>"
        )
    
    def apply_filter(self):
        ft = self.filter_cb.currentText()
        for i in range(self.model.rowCount()):
            issue = self.model.item(i, 3).text()
            if ft == "All":
                self.table.setRowHidden(i, False)
            else:
                self.table.setRowHidden(i, not issue.startswith(ft))
    
    def scan_done(self):
        self.btn_scan.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.pbar.setValue(100)
        self.log("[DONE] Complete!")
        
        if len(self.rows) == 0:
            QMessageBox.information(self, "Done", "No issues found!")
        else:
            QMessageBox.information(self, "Done", f"Found {len(self.rows)} issues")
    
    def export(self):
        if not self.rows:
            QMessageBox.information(self, "Export", "No data")
            return
        
        fp, _ = QFileDialog.getSaveFileName(self, "Export", "qa_results.csv", "CSV (*.csv)")
        if not fp:
            return
        
        try:
            import csv
            with open(fp, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(["File", "JP Line", "MTL Line", "Issue", "JP", "MTL", "Suggestion", "Severity"])
                for r in self.rows:
                    w.writerow([
                        r['file'], r['line'], r.get('mtl_line', r['line']), r['issue'], 
                        r['jp_text'], r['mtl_text'], 
                        r['suggestion'], r['severity']
                    ])
            self.log(f"[INFO] Exported: {fp}")
            QMessageBox.information(self, "Done", f"Exported to:\n{fp}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.log(f"[ERROR] Export failed: {str(e)}")

# ============================================================================
# CRASH HANDLER
# ============================================================================
def excepthook(exc_type, exc_value, exc_tb):
    log_path = os.path.join(os.getenv('TEMP', '/tmp'), 'JLH_crash.log')
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(''.join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        QMessageBox.critical(None, 'Crash', f"Error logged to:\n{log_path}")
    except:
        pass

sys.excepthook = excepthook

# ============================================================================
# MAIN
# ============================================================================
if __name__ == '__main__':
    # Suppress console output if frozen
    if hasattr(sys, 'frozen'):
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
    
    app = QApplication(sys.argv)
    app.setApplicationName("JP Leftover Hunter")
    
    win = MainWin()
    win.show()
    
    sys.exit(app.exec_())