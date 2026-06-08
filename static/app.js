const state = {
  jobId: "",
  file: null,
  filename: "",
  sourceUrl: "",
  stems: [],
  players: [],
  chords: [],
  activeChordIndex: -1,
  mixPlaying: false,
  mixStartedAt: 0,
  mixPausedAt: 0,
  jobs: [],
  tools: {},
  playToken: 0,
  analysisRunning: false,
  sessionStep: 0,
  sessionProcesses: [],
  masterVolume: Number(localStorage.getItem("detrace-master-volume") || 1),
  bassLevel: Number(localStorage.getItem("detrace-bass-level") || 0),
  trebleLevel: Number(localStorage.getItem("detrace-treble-level") || 0),
  seeking: false,
  loopEnabled: localStorage.getItem("detrace-loop-enabled") === "1",
};

const els = {
  dropzone: document.querySelector("#dropzone"),
  fileInput: document.querySelector("#fileInput"),
  chooseBtn: document.querySelector("#chooseBtn"),
  exitBtn: document.querySelector("#exitBtn"),
  sourcePlayer: document.querySelector("#sourcePlayer"),
  splash: document.querySelector("#splash"),
  startAppBtn: document.querySelector("#startAppBtn"),
  separateBtn: document.querySelector("#separateBtn"),
  exportBtn: document.querySelector("#exportBtn"),
  playMixBtn: document.querySelector("#playMixBtn"),
  pauseBtn: document.querySelector("#pauseBtn"),
  stopMixBtn: document.querySelector("#stopMixBtn"),
  rewindBtn: document.querySelector("#rewindBtn"),
  loopBtn: document.querySelector("#loopBtn"),
  stems: document.querySelector("#stems"),
  uploadList: document.querySelector("#uploadList"),
  spectrumCanvas: document.querySelector("#spectrumCanvas"),
  chordTimeline: document.querySelector("#chordTimeline"),
  currentChord: document.querySelector("#currentChord"),
  pianoKeyboard: document.querySelector("#pianoKeyboard"),
  selectedSummary: document.querySelector("#selectedSummary"),
  volumeControl: document.querySelector("#volumeControl"),
  volumeValue: document.querySelector("#volumeValue"),
  seekControl: document.querySelector("#seekControl"),
  seekCurrent: document.querySelector("#seekCurrent"),
  seekDuration: document.querySelector("#seekDuration"),
  bassControl: document.querySelector("#bassControl"),
  bassValue: document.querySelector("#bassValue"),
  bassLed: document.querySelector("#bassLed"),
  trebleControl: document.querySelector("#trebleControl"),
  trebleValue: document.querySelector("#trebleValue"),
  trebleLed: document.querySelector("#trebleLed"),
  clearUploadsBtn: document.querySelector("#clearUploadsBtn"),
  modelSelect: document.querySelector("#modelSelect"),
  languageSelect: document.querySelector("#languageSelect"),
  log: document.querySelector("#log"),
  toolStatus: document.querySelector("#toolStatus"),
};

const translations = {
  en: {
    language: "Language",
    splashTitle: "Separate every voice and instrument.",
    splashCopy: "Analyze MP3 tracks, preview stems in sync, remove instruments, and export a clean custom mix.",
    start: "Start DeTrace",
    licenseText: "This project is open source and available under the MIT License.",
    authorText: "Author: Roberto Raimondo - IS Senior Systems Engineer II",
    rightsText: "© 2026 All Rights Reserved.",
    appTitle: "Stem separator and MP3 mixer",
    installTools: "Install Tools",
    dropTitle: "Drop an MP3 here",
    dropHint: "or choose a file to analyze vocals and instruments.",
    chooseMp3: "Choose MP3",
    original: "Original",
    selectedPreview: "Selected instrument preview",
    volume: "Volume",
    position: "Position",
    bass: "Bass",
    treble: "Treble",
    playSelected: "Play Selected",
    rewind: "Rewind",
    loop: "Loop",
    pause: "Pause",
    resume: "Resume",
    stop: "Stop",
    stemModel: "Stem model",
    modelCombined: "6 stems + Accordion",
    modelTrueAccordion: "Full instrument stems: MVSep Mega 53 local model",
    model6: "6 stems: vocals, drums, bass, guitar, piano, other",
    model4: "4 stems: vocals, drums, bass, other",
    modelAccordion: "Accordion only: MVSep local model",
    analyze: "Analyze",
    analyzeAgain: "Analyze Again",
    exportMp3: "Export MP3",
    extractChords: "Extract Chords",
    chords: "Chords",
    noChord: "No chord",
    detectingChords: "Detecting...",
    detectingChordsLog: "Extracting chords from the original MP3...",
    chordsReady: "Found {count} chord changes.",
    noChordsFound: "No clear chords found.",
    chordDetectionFailed: "Chord detection failed.",
    uploads: "Uploads",
    clear: "Clear",
    session: "Session",
    ready: "ready",
    missing: "missing",
    installing: "Installing...",
    installingTools: "Installing missing audio tools. This can take a few minutes...",
    toolInstallFailed: "Tool installation failed.",
    nothingNew: "nothing new",
    toolInstallComplete: "Tool installation complete: {installed}.",
    clearConfirm: "Clear all uploaded MP3s and analyzed tracks?",
    couldNotClearUploads: "Could not clear uploads.",
    uploadsCleared: "Uploaded MP3 list cleared.",
    emptyUploads: "No uploaded files yet.",
    tracksFound: "{count} tracks found",
    notAnalyzed: "Not analyzed",
    couldNotLoadUploads: "Could not load uploads.",
    couldNotLoadUploaded: "Could not load uploaded file.",
    loaded: "Loaded {filename}.",
    uploading: "Uploading {filename}...",
    uploadFailed: "Upload failed.",
    uploadComplete: "Upload complete. Analyzing instruments now...",
    analyzing: "Analyzing...",
    analyzingWithModel: "Analyzing the MP3 with {model}. This can take a few minutes.",
    checkingRequirements: "Checking analysis requirements...",
    requirementsReady: "Requirements are ready.",
    separationStarted: "Starting stem separation with {model}...",
    separationCached: "Using already analyzed stems for {model}.",
    separationStillRunning: "Stem separation is still running. Large songs and first runs can take several minutes.",
    separationReady: "Stem separation finished in {seconds}s.",
    renderingTracks: "Preparing {count} playable tracks: {tracks}.",
    chordsStarted: "Starting chord detection...",
    chordsFinished: "Chord detection finished in {seconds}s.",
    sessionReadyToPlay: "All sessions are completed. Now you can play your song.",
    accordionStarted: "Starting Accordion extraction...",
    accordionStillRunning: "Accordion extraction is still running. This model is slower than the 6-stem pass.",
    accordionFinished: "Accordion extraction finished in {seconds}s.",
    separationFailed: "Separation failed.",
    foundTracks: "Found {count} tracks: {tracks}.",
    select: "Select",
    noSelection: "No instruments selected",
    exporting: "Exporting...",
    exportingTracks: "Exporting selected tracks to MP3...",
    exportFailed: "Export failed.",
    exportDownloaded: "MP3 export downloaded.",
    couldNotDownload: "Could not download exported MP3.",
    audioLoadFailed: "Could not load audio: {track}.",
    audioPlayFailed: "Could not play audio: {track}.",
    audioPlaySkipped: "Audio was skipped after a playback interruption: {track}.",
    accordionPending: "6 stems are ready. Accordion is still processing...",
    accordionReady: "Accordion stem is ready.",
    accordionFailed: "Accordion stem failed.",
    couldNotReadStatus: "Could not read tool status.",
    exitApp: "Exit",
    exiting: "Closing DeTrace...",
    closed: "DeTrace is closed. You can close this tab.",
    exitFailed: "Could not close DeTrace cleanly.",
  },
  it: {
    language: "Lingua",
    splashTitle: "Separa ogni voce e strumento.",
    splashCopy: "Analizza brani MP3, ascolta le tracce in sincronia, rimuovi strumenti ed esporta un mix pulito.",
    start: "Avvia DeTrace",
    licenseText: "Questo progetto è open source e disponibile con licenza MIT.",
    authorText: "Autore: Roberto Raimondo - IS Senior Systems Engineer II",
    rightsText: "© 2026 Tutti i diritti riservati.",
    appTitle: "Separatore di tracce e mixer MP3",
    installTools: "Installa strumenti",
    dropTitle: "Trascina qui un MP3",
    dropHint: "oppure scegli un file per analizzare voci e strumenti.",
    chooseMp3: "Scegli MP3",
    original: "Originale",
    selectedPreview: "Anteprima strumenti selezionati",
    playSelected: "Riproduci selezionati",
    stop: "Stop",
    stemModel: "Modello tracce",
    model6: "6 tracce: voce, batteria, basso, chitarra, piano, altro",
    model4: "4 tracce: voce, batteria, basso, altro",
    analyzeAgain: "Analizza di nuovo",
    exportMp3: "Esporta MP3",
    extractChords: "Estrai accordi",
    chords: "Accordi",
    noChord: "Nessun accordo",
    uploads: "Caricamenti",
    clear: "Pulisci",
    session: "Sessione",
    ready: "pronto",
    missing: "mancante",
    select: "Seleziona",
    emptyUploads: "Nessun file caricato.",
    tracksFound: "{count} tracce trovate",
    notAnalyzed: "Non analizzato",
  },
  es: {
    language: "Idioma",
    splashTitle: "Separa cada voz e instrumento.",
    splashCopy: "Analiza pistas MP3, previsualiza stems sincronizados, elimina instrumentos y exporta una mezcla limpia.",
    start: "Iniciar DeTrace",
    licenseText: "Este proyecto es de código abierto y está disponible bajo la licencia MIT.",
    authorText: "Autor: Roberto Raimondo - IS Senior Systems Engineer II",
    rightsText: "© 2026 Todos los derechos reservados.",
    appTitle: "Separador de stems y mezclador MP3",
    installTools: "Instalar herramientas",
    dropTitle: "Suelta un MP3 aquí",
    dropHint: "o elige un archivo para analizar voces e instrumentos.",
    chooseMp3: "Elegir MP3",
    original: "Original",
    selectedPreview: "Vista previa de instrumentos seleccionados",
    playSelected: "Reproducir seleccionados",
    stop: "Detener",
    stemModel: "Modelo de stems",
    model6: "6 stems: voz, batería, bajo, guitarra, piano, otros",
    model4: "4 stems: voz, batería, bajo, otros",
    analyzeAgain: "Analizar otra vez",
    exportMp3: "Exportar MP3",
    extractChords: "Extraer acordes",
    chords: "Acordes",
    noChord: "Sin acorde",
    uploads: "Subidas",
    clear: "Borrar",
    session: "Sesión",
    ready: "listo",
    missing: "falta",
    select: "Seleccionar",
    emptyUploads: "Aún no hay archivos subidos.",
    tracksFound: "{count} pistas encontradas",
    notAnalyzed: "Sin analizar",
  },
  de: {
    language: "Sprache",
    splashTitle: "Trenne jede Stimme und jedes Instrument.",
    splashCopy: "Analysiere MP3-Titel, höre Stems synchron vor, entferne Instrumente und exportiere einen sauberen Mix.",
    start: "DeTrace starten",
    licenseText: "Dieses Projekt ist Open Source und unter der MIT-Lizenz verfügbar.",
    authorText: "Autor: Roberto Raimondo - IS Senior Systems Engineer II",
    rightsText: "© 2026 Alle Rechte vorbehalten.",
    appTitle: "Stem-Trenner und MP3-Mixer",
    installTools: "Tools installieren",
    dropTitle: "MP3 hier ablegen",
    dropHint: "oder eine Datei auswählen, um Stimmen und Instrumente zu analysieren.",
    chooseMp3: "MP3 auswählen",
    original: "Original",
    selectedPreview: "Vorschau ausgewählter Instrumente",
    playSelected: "Auswahl abspielen",
    stop: "Stopp",
    stemModel: "Stem-Modell",
    model6: "6 Stems: Gesang, Schlagzeug, Bass, Gitarre, Klavier, Sonstiges",
    model4: "4 Stems: Gesang, Schlagzeug, Bass, Sonstiges",
    analyzeAgain: "Erneut analysieren",
    exportMp3: "MP3 exportieren",
    extractChords: "Akkorde erkennen",
    chords: "Akkorde",
    noChord: "Kein Akkord",
    uploads: "Uploads",
    clear: "Leeren",
    session: "Sitzung",
    ready: "bereit",
    missing: "fehlt",
    select: "Auswählen",
    emptyUploads: "Noch keine Dateien hochgeladen.",
    tracksFound: "{count} Spuren gefunden",
    notAnalyzed: "Nicht analysiert",
  },
  fr: {
    language: "Langue",
    splashTitle: "Séparez chaque voix et instrument.",
    splashCopy: "Analysez des MP3, prévisualisez les stems en synchronisation, retirez des instruments et exportez un mix propre.",
    start: "Démarrer DeTrace",
    licenseText: "Ce projet est open source et disponible sous licence MIT.",
    authorText: "Auteur : Roberto Raimondo - IS Senior Systems Engineer II",
    rightsText: "© 2026 Tous droits réservés.",
    appTitle: "Séparateur de stems et mixeur MP3",
    installTools: "Installer les outils",
    dropTitle: "Déposez un MP3 ici",
    dropHint: "ou choisissez un fichier pour analyser les voix et instruments.",
    chooseMp3: "Choisir MP3",
    original: "Original",
    selectedPreview: "Aperçu des instruments sélectionnés",
    playSelected: "Lire la sélection",
    stop: "Arrêter",
    stemModel: "Modèle de stems",
    model6: "6 stems : voix, batterie, basse, guitare, piano, autre",
    model4: "4 stems : voix, batterie, basse, autre",
    analyzeAgain: "Analyser à nouveau",
    exportMp3: "Exporter MP3",
    extractChords: "Extraire les accords",
    chords: "Accords",
    noChord: "Aucun accord",
    uploads: "Téléversements",
    clear: "Effacer",
    session: "Session",
    ready: "prêt",
    missing: "manquant",
    select: "Sélectionner",
    emptyUploads: "Aucun fichier téléversé.",
    tracksFound: "{count} pistes trouvées",
    notAnalyzed: "Non analysé",
  },
  pt: {
    language: "Idioma",
    splashTitle: "Separe cada voz e instrumento.",
    splashCopy: "Analise faixas MP3, pré-visualize stems sincronizados, remova instrumentos e exporte uma mistura limpa.",
    start: "Iniciar DeTrace",
    licenseText: "Este projeto é open source e está disponível sob a licença MIT.",
    authorText: "Autor: Roberto Raimondo - IS Senior Systems Engineer II",
    rightsText: "© 2026 Todos os direitos reservados.",
    appTitle: "Separador de stems e mixer MP3",
    installTools: "Instalar ferramentas",
    dropTitle: "Solte um MP3 aqui",
    dropHint: "ou escolha um arquivo para analisar vozes e instrumentos.",
    chooseMp3: "Escolher MP3",
    original: "Original",
    selectedPreview: "Prévia dos instrumentos selecionados",
    playSelected: "Reproduzir selecionados",
    stop: "Parar",
    stemModel: "Modelo de stems",
    model6: "6 stems: vocais, bateria, baixo, guitarra, piano, outros",
    model4: "4 stems: vocais, bateria, baixo, outros",
    analyzeAgain: "Analisar novamente",
    exportMp3: "Exportar MP3",
    extractChords: "Extrair acordes",
    chords: "Acordes",
    noChord: "Sem acorde",
    uploads: "Uploads",
    clear: "Limpar",
    session: "Sessão",
    ready: "pronto",
    missing: "ausente",
    select: "Selecionar",
    emptyUploads: "Nenhum arquivo enviado.",
    tracksFound: "{count} faixas encontradas",
    notAnalyzed: "Não analisado",
  },
  zh: {
    language: "语言",
    splashTitle: "分离每一种人声和乐器。",
    splashCopy: "分析 MP3，同步预览音轨，移除乐器，并导出干净的自定义混音。",
    start: "启动 DeTrace",
    licenseText: "本项目为开源项目，采用 MIT 许可证。",
    authorText: "作者：Roberto Raimondo - IS Senior Systems Engineer II",
    rightsText: "© 2026 保留所有权利。",
    appTitle: "音轨分离器和 MP3 混音器",
    installTools: "安装工具",
    dropTitle: "将 MP3 拖到这里",
    dropHint: "或选择文件来分析人声和乐器。",
    chooseMp3: "选择 MP3",
    original: "原始音频",
    selectedPreview: "所选乐器预览",
    playSelected: "播放所选",
    stop: "停止",
    stemModel: "音轨模型",
    model6: "6 轨：人声、鼓、贝斯、吉他、钢琴、其他",
    model4: "4 轨：人声、鼓、贝斯、其他",
    analyzeAgain: "重新分析",
    exportMp3: "导出 MP3",
    extractChords: "提取和弦",
    chords: "和弦",
    noChord: "无和弦",
    uploads: "上传",
    clear: "清除",
    session: "会话",
    ready: "就绪",
    missing: "缺失",
    select: "选择",
    emptyUploads: "尚未上传文件。",
    tracksFound: "找到 {count} 条音轨",
    notAnalyzed: "未分析",
  },
  ja: {
    language: "言語",
    splashTitle: "すべての声と楽器を分離します。",
    splashCopy: "MP3 を解析し、ステムを同期プレビューし、楽器を除去してきれいなミックスを書き出します。",
    start: "DeTrace を開始",
    licenseText: "このプロジェクトはオープンソースで、MIT ライセンスで提供されています。",
    authorText: "作者: Roberto Raimondo - IS Senior Systems Engineer II",
    rightsText: "© 2026 All Rights Reserved.",
    appTitle: "ステム分離と MP3 ミキサー",
    installTools: "ツールをインストール",
    dropTitle: "MP3 をここにドロップ",
    dropHint: "またはファイルを選んで声と楽器を解析します。",
    chooseMp3: "MP3 を選択",
    original: "オリジナル",
    selectedPreview: "選択した楽器のプレビュー",
    playSelected: "選択を再生",
    stop: "停止",
    stemModel: "ステムモデル",
    model6: "6 ステム: ボーカル、ドラム、ベース、ギター、ピアノ、その他",
    model4: "4 ステム: ボーカル、ドラム、ベース、その他",
    analyzeAgain: "再解析",
    exportMp3: "MP3 を書き出し",
    extractChords: "コードを抽出",
    chords: "コード",
    noChord: "コードなし",
    uploads: "アップロード",
    clear: "クリア",
    session: "セッション",
    ready: "準備完了",
    missing: "不足",
    select: "選択",
    emptyUploads: "アップロードされたファイルはありません。",
    tracksFound: "{count} トラック検出",
    notAnalyzed: "未解析",
  },
  ko: {
    language: "언어",
    splashTitle: "모든 보컬과 악기를 분리합니다.",
    splashCopy: "MP3를 분석하고 스템을 동기화해 미리 듣고, 악기를 제거한 뒤 깨끗한 믹스를 내보냅니다.",
    start: "DeTrace 시작",
    licenseText: "이 프로젝트는 오픈 소스이며 MIT 라이선스로 제공됩니다.",
    authorText: "작성자: Roberto Raimondo - IS Senior Systems Engineer II",
    rightsText: "© 2026 모든 권리 보유.",
    appTitle: "스템 분리기 및 MP3 믹서",
    installTools: "도구 설치",
    dropTitle: "MP3를 여기에 놓기",
    dropHint: "또는 파일을 선택해 보컬과 악기를 분석하세요.",
    chooseMp3: "MP3 선택",
    original: "원본",
    selectedPreview: "선택한 악기 미리 듣기",
    playSelected: "선택 재생",
    stop: "정지",
    stemModel: "스템 모델",
    model6: "6 스템: 보컬, 드럼, 베이스, 기타, 피아노, 기타",
    model4: "4 스템: 보컬, 드럼, 베이스, 기타",
    analyzeAgain: "다시 분석",
    exportMp3: "MP3 내보내기",
    extractChords: "코드 추출",
    chords: "코드",
    noChord: "코드 없음",
    uploads: "업로드",
    clear: "지우기",
    session: "세션",
    ready: "준비됨",
    missing: "없음",
    select: "선택",
    emptyUploads: "아직 업로드된 파일이 없습니다.",
    tracksFound: "{count}개 트랙 발견",
    notAnalyzed: "분석 안 됨",
  },
  ar: {
    language: "اللغة",
    splashTitle: "افصل كل صوت وكل آلة.",
    splashCopy: "حلّل ملفات MP3، واستمع إلى المسارات بتزامن، واحذف الآلات، ثم صدّر مزيجًا نظيفًا.",
    start: "بدء DeTrace",
    licenseText: "هذا المشروع مفتوح المصدر ومتاح بموجب ترخيص MIT.",
    authorText: "المؤلف: Roberto Raimondo - IS Senior Systems Engineer II",
    rightsText: "© 2026 جميع الحقوق محفوظة.",
    appTitle: "فاصل المسارات ومزج MP3",
    installTools: "تثبيت الأدوات",
    dropTitle: "أسقط ملف MP3 هنا",
    dropHint: "أو اختر ملفًا لتحليل الأصوات والآلات.",
    chooseMp3: "اختيار MP3",
    original: "الأصل",
    selectedPreview: "معاينة الآلات المحددة",
    playSelected: "تشغيل المحدد",
    stop: "إيقاف",
    stemModel: "نموذج المسارات",
    model6: "6 مسارات: غناء، طبول، باس، غيتار، بيانو، أخرى",
    model4: "4 مسارات: غناء، طبول، باس، أخرى",
    analyzeAgain: "تحليل مجددًا",
    exportMp3: "تصدير MP3",
    extractChords: "استخراج الأوتار",
    chords: "الأوتار",
    noChord: "لا وتر",
    uploads: "التحميلات",
    clear: "مسح",
    session: "الجلسة",
    ready: "جاهز",
    missing: "مفقود",
    select: "تحديد",
    emptyUploads: "لا توجد ملفات محملة بعد.",
    tracksFound: "تم العثور على {count} مسارات",
    notAnalyzed: "غير محلل",
  },
  hi: {
    language: "भाषा",
    splashTitle: "हर आवाज़ और वाद्य अलग करें।",
    splashCopy: "MP3 ट्रैक का विश्लेषण करें, stems को साथ सुनें, वाद्य हटाएँ और साफ़ कस्टम मिक्स निर्यात करें।",
    start: "DeTrace शुरू करें",
    licenseText: "यह प्रोजेक्ट open source है और MIT License के अंतर्गत उपलब्ध है।",
    authorText: "लेखक: Roberto Raimondo - IS Senior Systems Engineer II",
    rightsText: "© 2026 सर्वाधिकार सुरक्षित।",
    appTitle: "Stem separator और MP3 mixer",
    installTools: "Tools install करें",
    dropTitle: "MP3 यहाँ छोड़ें",
    dropHint: "या आवाज़ और वाद्य विश्लेषण करने के लिए फ़ाइल चुनें।",
    chooseMp3: "MP3 चुनें",
    original: "मूल",
    selectedPreview: "चयनित वाद्य preview",
    playSelected: "चयनित चलाएँ",
    stop: "रोकें",
    stemModel: "Stem model",
    model6: "6 stems: vocals, drums, bass, guitar, piano, other",
    model4: "4 stems: vocals, drums, bass, other",
    analyzeAgain: "फिर विश्लेषण करें",
    exportMp3: "MP3 export करें",
    extractChords: "Chords निकालें",
    chords: "Chords",
    noChord: "कोई chord नहीं",
    uploads: "Uploads",
    clear: "साफ़ करें",
    session: "Session",
    ready: "तैयार",
    missing: "अनुपलब्ध",
    select: "चुनें",
    emptyUploads: "अभी कोई फ़ाइल upload नहीं है।",
    tracksFound: "{count} tracks मिले",
    notAnalyzed: "विश्लेषित नहीं",
  },
  ru: {
    language: "Язык",
    splashTitle: "Разделяйте каждый голос и инструмент.",
    splashCopy: "Анализируйте MP3, прослушивайте дорожки синхронно, удаляйте инструменты и экспортируйте чистый микс.",
    start: "Запустить DeTrace",
    licenseText: "Этот проект открыт и доступен по лицензии MIT.",
    authorText: "Автор: Roberto Raimondo - IS Senior Systems Engineer II",
    rightsText: "© 2026 Все права защищены.",
    appTitle: "Разделитель stem-дорожек и MP3-микшер",
    installTools: "Установить инструменты",
    dropTitle: "Перетащите MP3 сюда",
    dropHint: "или выберите файл для анализа вокала и инструментов.",
    chooseMp3: "Выбрать MP3",
    original: "Оригинал",
    selectedPreview: "Просмотр выбранных инструментов",
    playSelected: "Воспроизвести выбранное",
    stop: "Стоп",
    stemModel: "Модель stems",
    model6: "6 stems: вокал, ударные, бас, гитара, пианино, другое",
    model4: "4 stems: вокал, ударные, бас, другое",
    analyzeAgain: "Анализировать снова",
    exportMp3: "Экспорт MP3",
    extractChords: "Извлечь аккорды",
    chords: "Аккорды",
    noChord: "Нет аккорда",
    uploads: "Загрузки",
    clear: "Очистить",
    session: "Сессия",
    ready: "готово",
    missing: "нет",
    select: "Выбрать",
    emptyUploads: "Файлы еще не загружены.",
    tracksFound: "Найдено дорожек: {count}",
    notAnalyzed: "Не анализировано",
  },
};

const toolLabels = {
  demucs: "Demucs",
  mvsepAccordion: "MVSep Accordion",
  ffmpeg: "FFmpeg",
  codecs: "Codecs",
  chords: "Chords",
};

let currentLanguage = localStorage.getItem("detrace-language") || "en";

const visualizer = {
  frame: 0,
  chordFrame: 0,
  context: null,
  nodes: new Map(),
  mixData: null,
};

const noteNames = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const flatToSharp = {
  Db: "C#",
  Eb: "D#",
  Gb: "F#",
  Ab: "G#",
  Bb: "A#",
};
const chordIntervals = {
  major: [0, 4, 7],
  minor: [0, 3, 7],
};
const mixSyncToleranceSeconds = 0.045;
const playedStemPeakThreshold = 10;

function t(key, values = {}) {
  const text = translations[currentLanguage]?.[key] || translations.en[key] || key;
  return Object.entries(values).reduce((output, [name, value]) => {
    return output.replaceAll(`{${name}}`, String(value));
  }, text);
}

function applyLanguage() {
  document.documentElement.lang = currentLanguage;
  document.documentElement.dir = currentLanguage === "ar" ? "rtl" : "ltr";
  els.languageSelect.value = currentLanguage;
  for (const element of document.querySelectorAll("[data-i18n]")) {
    element.textContent = t(element.dataset.i18n);
  }
  updateTools(state.tools);
  renderJobs();
  renderStems();
  renderChords();
  updateSelectedSummary();
  updatePauseButton();
  localStorage.setItem("detrace-language", currentLanguage);
}

function buildPianoKeyboard() {
  els.pianoKeyboard.innerHTML = "";
  let whiteIndex = 0;
  for (let midi = 21; midi <= 108; midi += 1) {
    const pitchClass = midi % 12;
    const octave = Math.floor(midi / 12) - 1;
    const noteName = noteNames[pitchClass];
    const note = `${noteName}${octave}`;
    const isBlack = noteName.includes("#");
    const key = document.createElement("span");
    key.className = `pianoKey ${isBlack ? "black" : "white"}`;
    key.dataset.midi = String(midi);
    key.dataset.pitchClass = String(pitchClass);
    key.dataset.note = note;
    key.title = note;
    key.setAttribute("aria-label", note);
    key.setAttribute("aria-pressed", "false");
    if (isBlack) {
      key.style.setProperty("--black-left", String(whiteIndex));
    } else {
      key.style.setProperty("--white-index", String(whiteIndex));
      whiteIndex += 1;
    }
    if (note === "A0" || note === "C4" || note === "C8") {
      key.textContent = note;
    }
    els.pianoKeyboard.append(key);
  }
}

function chordMidiNotes(chordName) {
  const normalized = String(chordName || "");
  const match = normalized.match(/^([A-G](?:#|b)?)(m?)/);
  if (!match || normalized === "N") return new Set();
  const rootName = flatToSharp[match[1]] || match[1];
  const root = noteNames.indexOf(rootName);
  if (root < 0) return new Set();
  const intervals = match[2] === "m" ? chordIntervals.minor : chordIntervals.major;
  const middleRoot = 60 + root;
  const rootMidi = middleRoot > 67 ? middleRoot - 12 : middleRoot;
  return new Set(intervals.map((interval) => rootMidi + interval));
}

function updatePianoKeyboard(chordName) {
  const activeMidiNotes = chordMidiNotes(chordName);
  for (const key of els.pianoKeyboard.querySelectorAll(".pianoKey")) {
    const isActive = activeMidiNotes.has(Number(key.dataset.midi));
    key.classList.toggle("active", isActive);
    key.setAttribute("aria-pressed", isActive ? "true" : "false");
  }
}

function audioLabel(audio) {
  return audio.dataset.track || audio.currentSrc || audio.src || "track";
}

function mediaSource(src) {
  if (!src || src.startsWith("blob:") || src.startsWith("http://") || src.startsWith("https://")) {
    return src || "";
  }
  return new URL(src, window.location.origin).href;
}

function prepareAudioOutput(audio) {
  audio.muted = false;
  audio.defaultMuted = false;
  if (!playerForAudio(audio)) {
    audio.volume = 1;
  }
  ensureAudioNode(audio);
  applyPreviewGain();
}

function setAudioSource(audio, src, label = "") {
  const source = mediaSource(src);
  const version = String((Number(audio.dataset.sourceVersion) || 0) + 1);
  audio.pause();
  prepareAudioOutput(audio);
  audio.dataset.sourceVersion = version;
  audio.dataset.track = label;
  audio.loop = false;
  audio.src = source;
  audio.load();
  updatePauseButton();
  audio.addEventListener("play", () => {
    if (audio.dataset.sourceVersion !== version || !audio.currentSrc) return;
    startSpectrum();
    startChordTracking();
  }, { once: true });
  audio.addEventListener("error", () => {
    if (audio.dataset.sourceVersion !== version || !source) return;
    log(t("audioLoadFailed", { track: audioLabel(audio) }), "error");
  }, { once: true });
  audio.addEventListener("loadedmetadata", updateSeekControl, { once: true });
  updateSeekControl();
}

function nextSessionStep() {
  state.sessionStep += 1;
  return state.sessionStep;
}

function renderSessionLog() {
  els.log.innerHTML = "";
  for (const entry of [...state.sessionProcesses].sort((left, right) => right.step - left.step)) {
    const item = document.createElement("li");
    item.textContent = `${entry.step}. ${entry.message}`;
    if (entry.type) item.className = entry.type;
    els.log.append(item);
  }
}

function log(message, type = "", options = {}) {
  if (options.consoleOnly) {
    if (type === "error") {
      console.error(message);
    } else {
      console.log(message);
    }
    return;
  }
  state.sessionProcesses.push({
    step: nextSessionStep(),
    message,
    type,
  });
  renderSessionLog();
}

function logProcess(message, type = "") {
  state.sessionProcesses.push({
    step: nextSessionStep(),
    message,
    type,
  });
  renderSessionLog();
}

function elapsedSeconds(startedAt) {
  return Math.max(1, Math.round((performance.now() - startedAt) / 1000));
}

function showSessionSongTitle(filename) {
  console.log(filename || state.filename || "");
}

function updateSelectedSummary() {
  const selected = state.stems.filter((stem) => stem.active).map((stem) => stem.name);
  els.selectedSummary.textContent = selected.length ? selected.join(", ") : t("noSelection");
}

function stopAllAudio() {
  stopMix();
  for (const audio of [els.sourcePlayer, ...state.players.map(({ audio }) => audio)]) {
    audio.pause();
    audio.currentTime = 0;
  }
  updateSeekControl();
}

function unloadAudio(audio) {
  if (!audio) return;
  audio.pause();
  audio.removeAttribute("src");
  audio.load();
}

function releaseLoadedAudio() {
  stopMix();
  for (const { audio } of state.players) {
    unloadAudio(audio);
  }
  unloadAudio(els.sourcePlayer);
}

function disableAppControls() {
  for (const button of document.querySelectorAll("button")) {
    button.disabled = true;
  }
  els.fileInput.disabled = true;
  els.modelSelect.disabled = true;
  els.languageSelect.disabled = true;
}

async function exitApplication() {
  stopAllAudio();
  setBusy(els.exitBtn, true, t("exiting"));
  disableAppControls();
  log(t("exiting"));

  try {
    if (window.pywebview?.api?.exit_app) {
      await window.pywebview.api.exit_app();
    } else if (window.pywebview?.api?.exitApp) {
      await window.pywebview.api.exitApp();
    } else {
      await fetch("/api/shutdown", { method: "POST" });
      window.close();
    }
    document.body.classList.add("appClosed");
    state.sessionProcesses = [];
    state.sessionStep = 0;
    renderSessionLog();
    log(t("closed"), "success");
  } catch (error) {
    els.exitBtn.disabled = false;
    els.exitBtn.classList.remove("working");
    els.fileInput.disabled = false;
    els.modelSelect.disabled = false;
    els.languageSelect.disabled = false;
    log(error.message || t("exitFailed"), "error");
  }
}

function setBusy(button, busy, label) {
  button.disabled = busy;
  button.classList.toggle("working", busy);
  button.setAttribute("aria-busy", busy ? "true" : "false");
  if (label) button.textContent = label;
}

function updateTools(tools = {}) {
  state.tools = tools || {};
  for (const badge of els.toolStatus.querySelectorAll("[data-tool]")) {
    const name = badge.dataset.tool;
    const ready = Boolean(tools[name]);
    badge.classList.toggle("ready", ready);
    badge.classList.toggle("missing", !ready);
    badge.textContent = `${toolLabels[name] || name} ${ready ? t("ready") : t("missing")}`;
  }
  updatePerformanceBadges(tools.performance || {});
}

function updatePerformanceBadges(performance = {}) {
  for (const badge of els.toolStatus.querySelectorAll("[data-metric]")) {
    const name = badge.dataset.metric;
    const metric = performance[name] || {};
    badge.classList.add("metric");
    badge.classList.toggle("ready", name === "gpu" ? Boolean(metric.available) : true);
    badge.classList.toggle("missing", name === "gpu" && !metric.available);
    badge.textContent = metric.label || name.toUpperCase();
    badge.title = badge.textContent;
  }
}

async function getStatus() {
  const response = await fetch("/api/status");
  const data = await response.json();
  updateTools(data.tools);
  return data.tools;
}

function startStatusPolling() {
  const refresh = () => {
    getStatus().catch(() => {});
    window.setTimeout(refresh, state.analysisRunning ? 1000 : 3000);
  };
  window.setTimeout(refresh, 3000);
}

function toolsReady(tools = {}, model = els.modelSelect?.value || "mvsep_true_accordion") {
  const separationReady = model === "htdemucs_6s_accordion"
    ? tools.demucs && tools.mvsepAccordion
    : model === "mvsep_true_accordion"
      ? tools.mvsepTrueAccordion
    : model === "mvsep_accordion"
      ? tools.mvsepAccordion
      : tools.demucs;
  return Boolean(separationReady && tools.ffmpeg && tools.codecs && tools.chords);
}

async function ensureToolsReady() {
  log(t("checkingRequirements"));
  const tools = await getStatus();
  const model = els.modelSelect?.value || "mvsep_true_accordion";
  if (toolsReady(tools, model)) {
    log(t("requirementsReady"), "success");
    return true;
  }
  const required = model === "htdemucs_6s_accordion"
    ? ["demucs", "mvsepAccordion", "ffmpeg", "codecs", "chords"]
    : model === "mvsep_true_accordion"
    ? ["mvsepTrueAccordion", "ffmpeg", "codecs", "chords"]
    : model === "mvsep_accordion"
    ? ["mvsepAccordion", "ffmpeg", "codecs", "chords"]
    : ["demucs", "ffmpeg", "codecs", "chords"];
  const missing = required
    .filter((key) => !tools[key])
    .map((key) => toolLabels[key] || key)
    .join(", ");
  log(`Missing requirements: ${missing}. Run setup or install requirements before using DeTrace.`, "error");
  return false;
}

async function loadJobs() {
  const response = await fetch("/api/jobs");
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || t("couldNotLoadUploads"));
  state.jobs = data.jobs;
  updateTools(data.tools);
  renderJobs();
}

async function clearUploads() {
  if (!state.jobs.length) return;
  const confirmed = window.confirm(t("clearConfirm"));
  if (!confirmed) return;

  releaseLoadedAudio();
  const response = await fetch("/api/jobs", { method: "DELETE" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || t("couldNotClearUploads"));

  state.jobId = "";
  state.file = null;
  state.filename = "";
  state.sourceUrl = "";
  state.stems = [];
  state.chords = [];
  state.activeChordIndex = -1;
  state.players = [];
  state.jobs = data.jobs || [];
  state.sessionStep = 0;
  state.sessionProcesses = [];
  setAudioSource(els.sourcePlayer, "", t("original"));
  els.stems.innerHTML = "";
  els.separateBtn.disabled = true;
  els.exportBtn.disabled = true;
  els.playMixBtn.disabled = true;
  els.stopMixBtn.disabled = true;
  updateTools(data.tools);
  renderJobs();
  renderChords();
  renderSessionLog();
  updateSeekControl();
  log(t("uploadsCleared"), "success");
}

function renderJobs() {
  els.uploadList.innerHTML = "";
  if (!state.jobs.length) {
    const empty = document.createElement("p");
    empty.className = "emptyUploads";
    empty.textContent = t("emptyUploads");
    els.uploadList.append(empty);
    return;
  }

  for (const job of state.jobs) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "uploadItem";
    button.dataset.jobId = job.jobId;
    button.classList.toggle("active", job.jobId === state.jobId);

    const title = document.createElement("span");
    title.className = "uploadName";
    title.textContent = job.filename;

    const meta = document.createElement("span");
    meta.className = "uploadMeta";
    meta.textContent = job.analyzed ? t("tracksFound", { count: job.stems.length }) : t("notAnalyzed");

    button.append(title, meta);
    els.uploadList.append(button);
  }
}

function selectUploadFromList(event) {
  const button = event.target.closest(".uploadItem");
  if (!button) return;
  const job = state.jobs.find((item) => item.jobId === button.dataset.jobId);
  if (!job) return;
  event.preventDefault();
  selectJob(job).catch((error) => log(error.message, "error"));
}

function loadJobIntoView(job) {
  stopMix();
  state.jobId = job.jobId;
  state.filename = job.filename;
  state.sourceUrl = job.sourceUrl;
  state.file = null;
  state.stems = (job.stems || []).map((stem) => ({ ...stem, active: defaultStemActive(stem) }));
  state.chords = job.chords || [];
  state.activeChordIndex = -1;
  setAudioSource(els.sourcePlayer, job.sourceUrl, job.filename || t("original"));
  renderStems();
  renderChords();
  syncPlayers();
  els.separateBtn.disabled = false;
  els.stopMixBtn.disabled = !state.stems.length;
  renderJobs();
}

async function selectJob(job) {
  try {
    const response = await fetch(`/api/jobs/${job.jobId}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || t("couldNotLoadUploaded"));
    updateTools(data.tools);
    loadJobIntoView(data.job);
    if (data.job.analyzed && !state.chords.length) {
      await loadChordsForCurrentJob();
    }
    showSessionSongTitle(data.job.filename);
  } catch (error) {
    log(error.message, "error");
  }
}

async function loadChordsForCurrentJob() {
  const startedAt = performance.now();
  logProcess(t("chordsStarted"));
  log(t("detectingChordsLog"));
  const chordResult = await postJson("/api/chords", { jobId: state.jobId });
  updateTools(chordResult.data.tools || {});
  if (!chordResult.response.ok) {
    log(chordResult.data.details || chordResult.data.error || t("chordDetectionFailed"), "error");
    return false;
  }
  state.chords = chordResult.data.chords || [];
  renderChords();
  log(t("chordsFinished", { seconds: elapsedSeconds(startedAt) }), "success");
  log(state.chords.length ? t("chordsReady", { count: state.chords.length }) : t("noChordsFound"), "success");
  state.jobs = state.jobs.map((job) => {
    if (job.jobId !== state.jobId) return job;
    return { ...job, chords: state.chords };
  });
  return true;
}

async function uploadFile(file) {
  els.log.innerHTML = "";
  state.sessionStep = 0;
  state.sessionProcesses = [];
  state.file = file;
  state.filename = file.name;
  state.stems = [];
  state.chords = [];
  state.activeChordIndex = -1;
  state.players = [];
  els.stems.innerHTML = "";
  renderChords();
  els.stems.setAttribute("aria-busy", "true");
  setAudioSource(els.sourcePlayer, URL.createObjectURL(file), file.name || t("original"));
  els.separateBtn.disabled = true;
  els.exportBtn.disabled = true;
  els.playMixBtn.disabled = true;
  els.stopMixBtn.disabled = true;
  logProcess(t("uploading", { filename: file.name }));

  const response = await fetch("/api/upload", {
    method: "POST",
    headers: { "X-Filename": encodeURIComponent(file.name || "audio.mp3") },
    body: file,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || t("uploadFailed"));

  state.jobId = data.jobId;
  state.filename = data.filename;
  state.sourceUrl = data.sourceUrl;
  setAudioSource(els.sourcePlayer, data.sourceUrl, data.filename || t("original"));
  updateTools(data.tools);
  state.jobs = [{ ...data, stems: [], analyzed: false }, ...state.jobs.filter((job) => job.jobId !== data.jobId)];
  renderJobs();
  log(t("uploadComplete"), "success");
  if (await ensureToolsReady()) {
    await separate();
  }
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  return { response, data };
}

async function separate() {
  if (state.analysisRunning) {
    log("Analysis is already running.");
    return;
  }
  const model = els.modelSelect.value;
  const separationModel = model === "htdemucs_6s_accordion" ? "htdemucs_6s" : model;
  const startedAt = performance.now();
  state.analysisRunning = true;
  setBusy(els.separateBtn, true, t("analyzing"));
  els.exportBtn.disabled = true;
  els.playMixBtn.disabled = true;
  els.stopMixBtn.disabled = true;
  if (!state.stems.length) {
    els.stems.innerHTML = "";
  }
  state.chords = [];
  state.activeChordIndex = -1;
  renderChords();
  els.stems.setAttribute("aria-busy", "true");
  log(t("analyzingWithModel", { model }));
  logProcess(t("separationStarted", { model: separationModel }));
  const stillRunningTimer = window.setTimeout(() => {
    log(t("separationStillRunning"));
  }, 30000);

  try {
    const stemResult = await postJson("/api/separate", { jobId: state.jobId, model: separationModel });
    window.clearTimeout(stillRunningTimer);
    updateTools(stemResult.data.tools || {});

    if (stemResult.response.status === 424 && await ensureToolsReady()) {
      state.analysisRunning = false;
      return await separate();
    }
    if (!stemResult.response.ok) {
      throw new Error(stemResult.data.details || stemResult.data.error || t("separationFailed"));
    }
    if (!Array.isArray(stemResult.data.stems) || stemResult.data.stems.length === 0) {
      throw new Error(stemResult.data.details || "Stem separation finished without producing any tracks.");
    }

    const activeById = new Map(state.stems.map((stem) => [stem.id || stem.name, stem.active]));
    state.stems = stemResult.data.stems.map((stem) => ({
      ...stem,
      active: activeById.get(stem.id || stem.name) ?? defaultStemActive(stem),
    }));
    log(
      stemResult.data.cached
        ? t("separationCached", { model: separationModel })
        : t("separationReady", { seconds: elapsedSeconds(startedAt) }),
      "success",
    );
    log(t("renderingTracks", {
      count: state.stems.length,
      tracks: state.stems.map((stem) => stem.name).join(", "),
    }), "success");
    renderStems();
    els.exportBtn.disabled = false;
    els.playMixBtn.disabled = false;
    els.stopMixBtn.disabled = false;
    els.separateBtn.textContent = t("analyzeAgain");
    els.stems.removeAttribute("aria-busy");

    await loadJobs();
    state.jobs = state.jobs.map((job) => {
      if (job.jobId !== state.jobId) return job;
      return { ...job, stems: state.stems, chords: state.chords, analyzed: true };
    });
    showSessionSongTitle(state.filename);
    if (model === "htdemucs_6s_accordion") {
      await appendAccordionForCurrentJob();
    }
    if (await loadChordsForCurrentJob()) {
      log(t("sessionReadyToPlay"), "success");
    }
  } catch (error) {
    window.clearTimeout(stillRunningTimer);
    log(error.message, "error");
  } finally {
    window.clearTimeout(stillRunningTimer);
    state.analysisRunning = false;
    setBusy(els.separateBtn, false);
    if (!state.stems.length) {
      els.separateBtn.textContent = t("analyze");
    }
    els.stems.removeAttribute("aria-busy");
  }
}

function renderStems() {
  els.stems.innerHTML = "";
  state.players = [];

  for (const stem of state.stems) {
    const card = document.createElement("article");
    card.className = "stem";

    const header = document.createElement("div");
    header.className = "stemHeader";

    const name = document.createElement("p");
    name.className = "stemName";
    name.textContent = stem.name;

    const toggle = document.createElement("label");
    toggle.className = "toggle";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = stem.active;
    checkbox.dataset.stemKey = stemKey(stem);
    checkbox.addEventListener("change", () => {
      stem.active = checkbox.checked;
      applyStemSelectionRules(stem);
      updateStemControls();
      syncPlayers();
    });
    toggle.append(checkbox, t("select"));

    const audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "metadata";
    setAudioSource(audio, stem.url, stem.name);
    audio.addEventListener("play", () => {
      if (!isStemActive(stem) && !state.mixPlaying) {
        cancelAudioPlay(audio);
      } else {
        prepareAudioOutput(audio);
        applyPreviewGain();
      }
    });
    audio.addEventListener("loadedmetadata", updateSeekControl);
    audio.addEventListener("timeupdate", updateSeekControl);
    audio.addEventListener("seeked", updateSeekControl);
    audio.addEventListener("ended", handleMixPlaybackEnded);

    header.append(name, toggle);
    card.append(header, audio);
    els.stems.append(card);
    state.players.push({ stem, audio, card });
  }
  applyPreviewGain();
  updateSeekControl();
  updateSelectedSummary();
  updatePlayedStemHighlights();
}

function updateStemControls() {
  els.stems.querySelectorAll('input[type="checkbox"][data-stem-key]').forEach((checkbox) => {
    const stem = state.stems.find((item) => stemKey(item) === checkbox.dataset.stemKey);
    if (stem) checkbox.checked = Boolean(stem.active);
  });
  updateSelectedSummary();
}

const passingChordMaxSeconds = 1.6;

function simplifyChords(chords) {
  const merged = [];
  for (const chord of chords || []) {
    const current = {
      ...chord,
      start: Number(chord.start) || 0,
      end: Number(chord.end) || 0,
    };
    const previous = merged.at(-1);
    if (previous && previous.chord === current.chord) {
      previous.end = Math.max(previous.end, current.end);
      continue;
    }
    merged.push(current);
  }
  if (merged.length <= 2) return merged;

  const simplified = [];
  for (let index = 0; index < merged.length; index += 1) {
    const chord = merged[index];
    const duration = Math.max(0, chord.end - chord.start);
    const previous = simplified.at(-1);
    const next = merged[index + 1];

    if (duration < passingChordMaxSeconds) {
      if (previous && next && previous.chord === next.chord) {
        previous.end = next.end;
        index += 1;
        continue;
      }
      if (next) {
        next.start = chord.start;
        continue;
      }
      if (previous) {
        previous.end = chord.end;
        continue;
      }
    }

    simplified.push({ ...chord });
  }

  const finalChords = [];
  for (const chord of simplified) {
    const previous = finalChords.at(-1);
    if (previous && previous.chord === chord.chord) {
      previous.end = chord.end;
      continue;
    }
    finalChords.push(chord);
  }
  return finalChords;
}

function renderChords() {
  state.chords = simplifyChords(state.chords);
  els.chordTimeline.innerHTML = "";
  els.currentChord.textContent = t("noChord");
  state.activeChordIndex = -1;
  updatePianoKeyboard("");
  if (!state.chords.length) {
    const empty = document.createElement("p");
    empty.className = "emptyChords";
    empty.textContent = t("noChordsFound");
    els.chordTimeline.append(empty);
    return;
  }

  const total = Math.max(...state.chords.map((chord) => chord.end), 1);
  for (const chord of state.chords) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "chordItem";
    button.dataset.start = chord.start;
    button.dataset.end = chord.end;
    button.style.flexGrow = Math.max(chord.end - chord.start, 0.35);
    button.innerHTML = `<strong>${chord.chord}</strong><span>${formatTime(chord.start)}</span>`;
    button.title = `${formatTime(chord.start)} - ${formatTime(chord.end)}`;
    button.addEventListener("click", () => {
      els.sourcePlayer.currentTime = Math.min(chord.start, total);
      prepareAudioOutput(els.sourcePlayer);
      els.sourcePlayer.play().catch((error) => log(error.message, "error"));
    });
    els.chordTimeline.append(button);
  }
  updateCurrentChord();
}

function formatTime(seconds) {
  const whole = Math.max(0, Math.floor(Number(seconds) || 0));
  const minutes = Math.floor(whole / 60);
  return `${minutes}:${String(whole % 60).padStart(2, "0")}`;
}

function updateCurrentChord() {
  const time = playbackTime();
  let activeIndex = -1;
  for (let index = 0; index < state.chords.length; index += 1) {
    const chord = state.chords[index];
    const next = state.chords[index + 1];
    const end = Number.isFinite(Number(chord.end)) ? Number(chord.end) : next?.start;
    if (time >= chord.start && (end === undefined || time < end)) {
      activeIndex = index;
      break;
    }
    if (time >= chord.start) activeIndex = index;
  }
  const active = activeIndex >= 0 ? state.chords[activeIndex] : null;
  els.currentChord.textContent = active ? active.chord : t("noChord");
  updatePianoKeyboard(active?.chord || "");
  for (const [index, item] of [...els.chordTimeline.querySelectorAll(".chordItem")].entries()) {
    const start = Number(item.dataset.start);
    const isActive = index === activeIndex;
    item.classList.toggle("active", isActive);
    item.classList.toggle("played", time >= start);
    item.setAttribute("aria-current", isActive ? "true" : "false");
  }
  if (activeIndex !== state.activeChordIndex) {
    state.activeChordIndex = activeIndex;
    const activeItem = els.chordTimeline.querySelector(".chordItem.active");
    activeItem?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }
}

async function appendAccordionForCurrentJob() {
  const jobId = state.jobId;
  if (!jobId) return;
  const startedAt = performance.now();
  log(t("accordionPending"));
  logProcess(t("accordionStarted"));
  const stillRunningTimer = window.setTimeout(() => {
    log(t("accordionStillRunning"));
  }, 30000);
  try {
    const result = await postJson("/api/accordion", { jobId });
    updateTools(result.data.tools || {});
    if (result.response.status === 424 && await ensureToolsReady()) {
      return await appendAccordionForCurrentJob();
    }
    if (!result.response.ok) {
      log(result.data.details || result.data.error || t("accordionFailed"), "error");
      return;
    }
    if (state.jobId !== jobId) return;
    const activeById = new Map(state.stems.map((stem) => [stem.id || stem.name, stem.active]));
    state.stems = result.data.stems.map((stem) => ({
      ...stem,
      active: activeById.get(stem.id || stem.name) ?? defaultStemActive(stem),
    }));
    renderStems();
    syncPlayers();
    state.jobs = state.jobs.map((job) => {
      if (job.jobId !== jobId) return job;
      return { ...job, stems: state.stems, analyzed: true };
    });
    renderJobs();
    log(
      result.data.cached
        ? t("separationCached", { model: "Accordion" })
        : t("accordionFinished", { seconds: elapsedSeconds(startedAt) }),
      "success",
    );
    log(t("accordionReady"), "success");
  } finally {
    window.clearTimeout(stillRunningTimer);
  }
}

function applyNoAccordionCacheBust(stems) {
  const stamp = Date.now();
  return stems.map((stem) => {
    if (!isNoAccordionMix(stem)) return stem;
    const separator = stem.url.includes("?") ? "&" : "?";
    return { ...stem, url: `${stem.url}${separator}v=${stamp}` };
  });
}

function playbackTime() {
  return currentPlaybackTime();
}

function startChordTracking() {
  if (visualizer.chordFrame) return;
  trackChords();
}

function trackChords() {
  if (state.mixPlaying) {
    syncActivePlayerTimes();
  }
  updateCurrentChord();
  const sourcePlaying = !els.sourcePlayer.paused && !els.sourcePlayer.ended;
  if (sourcePlaying || state.mixPlaying) {
    visualizer.chordFrame = requestAnimationFrame(trackChords);
  } else {
    visualizer.chordFrame = 0;
  }
}

function activeMixPlayers() {
  return state.players.filter(({ stem }) => isStemActive(stem));
}

function playerForAudio(audio) {
  return state.players.find((player) => player.audio === audio) || null;
}

function stemKey(stem) {
  return stem?.id || stem?.name || "";
}

function normalizedStemName(stem) {
  return String(stem?.name || "").trim().toLowerCase();
}

function isAccordionStem(stem) {
  return normalizedStemName(stem) === "accordion";
}

function isNoAccordionMix(stem) {
  return normalizedStemName(stem) === "no accordion mix";
}

function isAccordionBleedStem(stem) {
  return ["piano", "other"].includes(normalizedStemName(stem));
}

function isTrueAccordionModelStem(stem) {
  return String(stemKey(stem)).startsWith("mvsep_true_accordion/");
}

function defaultStemActive(stem) {
  return !isNoAccordionMix(stem);
}

function hasAccordionStem() {
  return state.stems.some(isAccordionStem);
}

function applyStemSelectionRules(changedStem) {
  if (isTrueAccordionModelStem(changedStem)) return;

  if (isAccordionStem(changedStem)) {
    if (changedStem.active) {
      state.stems.forEach((stem) => {
        if (isNoAccordionMix(stem)) stem.active = false;
      });
      return;
    }
    state.stems.forEach((stem) => {
      if (isAccordionStem(stem) || isAccordionBleedStem(stem) || isNoAccordionMix(stem)) {
        stem.active = false;
      }
    });
    return;
  }

  if (isNoAccordionMix(changedStem) && changedStem.active) {
    state.stems.forEach((stem) => {
      if (stem !== changedStem && (isAccordionStem(stem) || isAccordionBleedStem(stem))) {
        stem.active = false;
      }
    });
    return;
  }

  if (isAccordionBleedStem(changedStem) && changedStem.active) {
    const accordion = state.stems.find(isAccordionStem);
    if (accordion && !accordion.active) {
      changedStem.active = false;
    }
  }
}

function currentStemFor(stem) {
  const key = stemKey(stem);
  return state.stems.find((item) => stemKey(item) === key) || stem;
}

function isStemActive(stem) {
  return Boolean(currentStemFor(stem)?.active);
}

function previewStemGain() {
  const count = Math.max(1, activeMixPlayers().length);
  const mixGain = count <= 1 ? 1 : Math.max(0.22, Math.min(0.92, 0.92 / Math.sqrt(count)));
  return mixGain * state.masterVolume;
}

function applyPreviewGain() {
  const gain = previewStemGain();
  if (els.sourcePlayer) {
    els.sourcePlayer.volume = 1;
    const sourceNode = visualizer.nodes.get(els.sourcePlayer);
    if (sourceNode?.gainNode) sourceNode.gainNode.gain.value = state.masterVolume;
  }
  for (const { stem, audio } of state.players) {
    audio.volume = 1;
    const node = visualizer.nodes.get(audio);
    if (node?.gainNode) node.gainNode.gain.value = isStemActive(stem) ? gain : 0;
    if (isStemActive(stem)) {
      audio.muted = false;
      audio.defaultMuted = false;
    } else {
      audio.muted = true;
      audio.defaultMuted = true;
    }
  }
}

function updateLoopButton() {
  if (!els.loopBtn) return;
  els.loopBtn.classList.toggle("active", state.loopEnabled);
  els.loopBtn.setAttribute("aria-pressed", state.loopEnabled ? "true" : "false");
}

function toggleLoop() {
  state.loopEnabled = !state.loopEnabled;
  localStorage.setItem("detrace-loop-enabled", state.loopEnabled ? "1" : "0");
  updateLoopButton();
}

function setMasterVolume(value) {
  const numeric = Number(value);
  state.masterVolume = Number.isFinite(numeric) ? Math.max(0, Math.min(1, numeric)) : 1;
  localStorage.setItem("detrace-master-volume", String(state.masterVolume));
  if (els.volumeControl) {
    els.volumeControl.value = String(Math.round(state.masterVolume * 100));
  }
  if (els.volumeValue) {
    els.volumeValue.textContent = `${Math.round(state.masterVolume * 100)}%`;
  }
  applyPreviewGain();
}

function clampToneLevel(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? Math.max(-12, Math.min(12, numeric)) : 0;
}

function updateToneLed(element, value) {
  if (!element) return;
  const lights = [...element.querySelectorAll("i")];
  const center = Math.floor(lights.length / 2);
  const steps = Math.round(Math.abs(value) / 12 * center);
  lights.forEach((light, index) => {
    light.className = "";
    const active = index === center
      || (value > 0 && index > center && index <= center + steps)
      || (value < 0 && index < center && index >= center - steps);
    light.classList.toggle("active", active);
    light.classList.toggle("positive", active && value > 0 && index > center);
    light.classList.toggle("negative", active && value < 0 && index < center);
    light.classList.toggle("center", index === center);
  });
}

function applyToneControls() {
  for (const node of visualizer.nodes.values()) {
    if (node.bassFilter) node.bassFilter.gain.value = state.bassLevel;
    if (node.trebleFilter) node.trebleFilter.gain.value = state.trebleLevel;
    if (node.gainNode) node.gainNode.gain.value = node.audio === els.sourcePlayer ? state.masterVolume : node.gainNode.gain.value;
  }
  applyPreviewGain();
}

function setToneLevel(kind, value) {
  const level = clampToneLevel(value);
  if (kind === "bass") {
    state.bassLevel = level;
    localStorage.setItem("detrace-bass-level", String(level));
    if (els.bassControl) els.bassControl.value = String(level);
    if (els.bassValue) els.bassValue.textContent = `${level > 0 ? "+" : ""}${level} dB`;
    updateToneLed(els.bassLed, level);
  } else {
    state.trebleLevel = level;
    localStorage.setItem("detrace-treble-level", String(level));
    if (els.trebleControl) els.trebleControl.value = String(level);
    if (els.trebleValue) els.trebleValue.textContent = `${level > 0 ? "+" : ""}${level} dB`;
    updateToneLed(els.trebleLed, level);
  }
  applyToneControls();
}

function shouldAudioPlay(audio, token) {
  const player = playerForAudio(audio);
  return Boolean(player && state.mixPlaying && audio.dataset.playToken === String(token));
}

function cancelAudioPlay(audio) {
  audio.dataset.playToken = "";
  audio.dataset.starting = "";
  audio.muted = true;
  audio.defaultMuted = true;
  audio.volume = 0;
  const node = visualizer.nodes.get(audio);
  if (node?.gainNode) node.gainNode.gain.value = 0;
  audio.pause();
}

function stopStaleAudio(audio, token) {
  if (shouldAudioPlay(audio, token)) {
    return true;
  }
  audio.pause();
  return false;
}

function mixMasterPlayer() {
  return activeMixPlayers().find(({ audio }) => (
    !audio.paused && !audio.ended && Number.isFinite(audio.currentTime)
  )) || state.players.find(({ audio }) => (
    !audio.paused && !audio.ended && Number.isFinite(audio.currentTime)
  )) || null;
}

function syncActivePlayerTimes() {
  const master = mixMasterPlayer();
  if (!master) return;
  const masterTime = master.audio.currentTime;
  for (const { audio } of state.players) {
    if (audio === master.audio || audio.paused || audio.ended) continue;
    const drift = audio.currentTime - masterTime;
    if (Math.abs(drift) > mixSyncToleranceSeconds) {
      audio.currentTime = masterTime;
    }
  }
}

function syncPlayers() {
  const hasSelection = state.stems.some((stem) => stem.active);
  const mixTime = currentMixTime();
  updateSelectedSummary();
  els.exportBtn.disabled = !hasSelection;
  els.playMixBtn.disabled = !hasSelection;
  els.stopMixBtn.disabled = !state.players.length;
  if (els.rewindBtn) els.rewindBtn.disabled = currentPlaybackDuration() <= 0;
  updatePauseButton();
  applyPreviewGain();
  for (const { stem, audio } of state.players) {
    if (!isStemActive(stem)) {
      audio.muted = true;
      audio.defaultMuted = true;
      audio.volume = 0;
      if (!state.mixPlaying) {
        cancelAudioPlay(audio);
      } else if ((audio.paused || audio.ended) && audio.dataset.starting !== "1") {
        audio.currentTime = mixTime;
        playAudioWithRetry(audio).catch((error) => logAudioPlayError(audio, error));
      } else if (Number.isFinite(audio.currentTime) && Math.abs(audio.currentTime - mixTime) > mixSyncToleranceSeconds) {
        audio.currentTime = mixTime;
      }
      continue;
    }
    audio.muted = false;
    audio.defaultMuted = false;
    if (state.mixPlaying) {
      if (audio.paused || audio.ended) {
        if (audio.dataset.starting !== "1") {
          audio.currentTime = mixTime;
          playAudioWithRetry(audio).then((started) => {
            if (!started && isStemActive(stem) && audio.dataset.starting !== "1") {
              log(t("audioPlaySkipped", { track: audioLabel(audio) }));
            }
          }).catch((error) => {
            logAudioPlayError(audio, error);
          });
        }
      } else if (Number.isFinite(audio.currentTime) && Math.abs(audio.currentTime - mixTime) > mixSyncToleranceSeconds) {
        audio.currentTime = mixTime;
      }
    }
  }
  applyPreviewGain();
  updatePlayedStemHighlights();
}

async function playAudioGroup(players) {
  const results = await Promise.allSettled(players.map(({ audio }) => playAudioWithRetry(audio)));
  const failed = results
    .map((result, index) => ({ result, player: players[index] }))
    .filter(({ result }) => result.status === "rejected");
  const started = results
    .filter((result) => result.status === "fulfilled")
    .some((result) => result.value === true);

  for (const { result, player } of failed) {
    logAudioPlayError(player.audio, result.reason);
  }

  return started;
}

function logAudioPlayError(audio, error) {
  if (interruptedPlay(error)) {
    return;
  }
  const reason = error?.message ? ` ${error.message}` : "";
  log(`${t("audioPlayFailed", { track: audioLabel(audio) })}${reason}`, "error");
}

function interruptedPlay(error) {
  const message = error?.message || "";
  return error?.name === "AbortError"
    || (/play\(\) request/i.test(message) && /(interrupt|pause|load)/i.test(message))
    || (/interrupt/i.test(message) && /(pause|load)/i.test(message));
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function playAudioWithRetry(audio) {
  if (audio.dataset.starting === "1") {
    return false;
  }
  const token = String(++state.playToken);
  audio.dataset.playToken = token;
  audio.dataset.starting = "1";
  try {
    for (let attempt = 0; attempt < 4; attempt += 1) {
      if (!shouldAudioPlay(audio, token)) {
        audio.muted = true;
        return false;
      }
      prepareAudioOutput(audio);
      applyPreviewGain();
      try {
        await audio.play();
        return stopStaleAudio(audio, token);
      } catch (error) {
        if (!interruptedPlay(error)) {
          throw error;
        }
        await sleep(120 + attempt * 120);
        if (!stopStaleAudio(audio, token) || (!state.mixPlaying && state.mixPausedAt <= 0)) {
          return false;
        }
      }
    }
    return false;
  } finally {
    if (audio.dataset.playToken === token) {
      audio.dataset.starting = "";
    }
  }
}

async function playMix() {
  const activePlayers = activeMixPlayers();
  if (!activePlayers.length) return;
  const players = state.players;
  if (!players.length) return;
  const startAt = currentPlaybackTime();
  els.sourcePlayer.pause();
  stopMix();
  state.mixPlaying = true;
  state.mixStartedAt = performance.now() - startAt * 1000;
  state.mixPausedAt = 0;
  for (const { audio } of players) {
    audio.currentTime = startAt;
  }
  applyPreviewGain();
  startSpectrum();
  startChordTracking();
  const anyPlaying = await playAudioGroup(players);
  if (!anyPlaying) {
    state.mixPlaying = false;
    state.mixStartedAt = 0;
    updatePauseButton();
    return;
  }
  syncActivePlayerTimes();
  updatePauseButton();
  updateSeekControl();
}

function stopMix() {
  for (const { audio } of state.players) {
    cancelAudioPlay(audio);
    audio.currentTime = 0;
  }
  state.mixPlaying = false;
  state.mixStartedAt = 0;
  state.mixPausedAt = 0;
  updateCurrentChord();
  updatePauseButton();
  updatePlayedStemHighlights();
  updateSeekControl();
}

function restartMixFrom(startAt = 0) {
  const players = state.players;
  if (!players.length) return;
  state.mixPlaying = true;
  state.mixStartedAt = performance.now() - startAt * 1000;
  state.mixPausedAt = 0;
  for (const { audio } of players) {
    audio.currentTime = startAt;
  }
  applyPreviewGain();
  startSpectrum();
  startChordTracking();
  playAudioGroup(players).then((started) => {
    if (!started) {
      state.mixPlaying = false;
      state.mixStartedAt = 0;
      updatePauseButton();
      updateSeekControl();
    }
  }).catch((error) => log(error.message, "error"));
}

function handleMixPlaybackEnded() {
  if (!state.mixPlaying) return;
  const activePlayers = activeMixPlayers();
  if (!activePlayers.length) return;
  const duration = mixDuration();
  const finished = activePlayers.every(({ audio }) => {
    const audioDuration = finiteDuration(audio) || duration;
    return audio.ended || audio.paused || audio.currentTime >= audioDuration - 0.08;
  });
  if (!finished && currentMixTime() < duration - 0.12) return;

  if (state.loopEnabled) {
    restartMixFrom(0);
    return;
  }

  state.mixPlaying = false;
  state.mixStartedAt = 0;
  state.mixPausedAt = 0;
  updateCurrentChord();
  updatePauseButton();
  updateSeekControl();
  updatePlayedStemHighlights();
}

function updatePauseButton() {
  if (!els.pauseBtn) return;
  const sourceActive = els.sourcePlayer.src && !els.sourcePlayer.ended && els.sourcePlayer.currentTime > 0;
  const players = state.players;
  const mixActive = state.mixPlaying || state.mixPausedAt > 0 || players.some(({ audio }) => audio.currentTime > 0);
  const canPause = Boolean(sourceActive || mixActive);
  const paused = sourceActive
    ? els.sourcePlayer.paused
    : Boolean(state.mixPausedAt || players.every(({ audio }) => audio.paused));
  els.pauseBtn.disabled = !canPause;
  els.pauseBtn.textContent = paused && canPause ? t("resume") : t("pause");
}

async function togglePause() {
  if (state.mixPlaying || state.mixPausedAt > 0) {
    await toggleMixPause();
    return;
  }
  if (!els.sourcePlayer.src) return;
  if (els.sourcePlayer.paused) {
    prepareAudioOutput(els.sourcePlayer);
    await els.sourcePlayer.play();
    startChordTracking();
  } else {
    els.sourcePlayer.pause();
  }
  updatePauseButton();
}

async function toggleMixPause() {
  const activePlayers = activeMixPlayers();
  if (!activePlayers.length) return;
  const players = state.players;
  if (!players.length) return;

  if (state.mixPlaying) {
    state.mixPausedAt = currentMixTime();
    for (const { audio } of players) {
      cancelAudioPlay(audio);
    }
    state.mixPlaying = false;
    state.mixStartedAt = 0;
    updateCurrentChord();
    updatePauseButton();
    return;
  }

  const resumeAt = state.mixPausedAt;
  state.mixPlaying = true;
  state.mixStartedAt = performance.now() - resumeAt * 1000;
  state.mixPausedAt = 0;
  for (const { audio } of players) {
    audio.currentTime = resumeAt;
  }
  applyPreviewGain();
  startSpectrum();
  startChordTracking();
  const anyPlaying = await playAudioGroup(players);
  if (!anyPlaying) {
    state.mixPlaying = false;
    state.mixStartedAt = 0;
    state.mixPausedAt = resumeAt;
    updatePauseButton();
    return;
  }
  syncActivePlayerTimes();
  updatePauseButton();
}

function currentMixTime() {
  const master = mixMasterPlayer();
  if (master && Number.isFinite(master.audio.currentTime)) return master.audio.currentTime;
  if (state.mixPausedAt > 0) return state.mixPausedAt;
  if (!state.mixPlaying || !state.mixStartedAt) return 0;
  const elapsed = (performance.now() - state.mixStartedAt) / 1000;
  const durations = state.players
    .map(({ audio }) => audio.duration)
    .filter((duration) => Number.isFinite(duration) && duration > 0);
  if (!durations.length) return elapsed;
  return Math.min(elapsed, Math.max(...durations));
}

function formatClock(seconds) {
  const safeSeconds = Number.isFinite(seconds) && seconds > 0 ? seconds : 0;
  const minutes = Math.floor(safeSeconds / 60);
  const wholeSeconds = Math.floor(safeSeconds % 60);
  return `${minutes}:${String(wholeSeconds).padStart(2, "0")}`;
}

function finiteDuration(audio) {
  return audio && Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : 0;
}

function mixDuration() {
  return Math.max(0, ...state.players.map(({ audio }) => finiteDuration(audio)));
}

function playerTimelineActive() {
  return state.mixPlaying
    || state.mixPausedAt > 0
    || state.players.some(({ audio }) => Number.isFinite(audio.currentTime) && audio.currentTime > 0);
}

function currentPlaybackDuration() {
  return playerTimelineActive() ? mixDuration() : Math.max(finiteDuration(els.sourcePlayer), mixDuration());
}

function currentPlaybackTime() {
  if (playerTimelineActive()) return currentMixTime();
  return Number.isFinite(els.sourcePlayer.currentTime) ? els.sourcePlayer.currentTime : 0;
}

function updateSeekControl() {
  if (!els.seekControl) return;
  const duration = currentPlaybackDuration();
  const current = Math.min(currentPlaybackTime(), duration || currentPlaybackTime());
  els.seekControl.disabled = duration <= 0;
  els.seekControl.max = String(duration || 0);
  if (!state.seeking) {
    els.seekControl.value = String(current || 0);
  }
  if (els.seekCurrent) {
    const displayCurrent = state.seeking ? Number(els.seekControl.value) : current;
    els.seekCurrent.textContent = formatClock(displayCurrent);
  }
  if (els.seekDuration) {
    els.seekDuration.textContent = formatClock(duration);
  }
  if (els.rewindBtn) {
    els.rewindBtn.disabled = duration <= 0;
  }
}

function seekTo(value) {
  const duration = currentPlaybackDuration();
  const target = Math.max(0, Math.min(Number(value) || 0, duration || Number(value) || 0));
  if (finiteDuration(els.sourcePlayer)) {
    els.sourcePlayer.currentTime = Math.min(target, finiteDuration(els.sourcePlayer));
  }
  for (const { audio } of state.players) {
    if (finiteDuration(audio)) {
      audio.currentTime = Math.min(target, finiteDuration(audio));
    }
  }
  if (state.mixPlaying) {
    state.mixStartedAt = performance.now() - target * 1000;
    syncPlayers();
  } else if (state.mixPausedAt > 0 || state.players.length) {
    state.mixPausedAt = target;
  }
  updateCurrentChord();
  updatePauseButton();
  updateSeekControl();
}

function rewindPlayback(seconds = 10) {
  seekTo(Math.max(0, currentPlaybackTime() - seconds));
}

async function exportMix() {
  setBusy(els.exportBtn, true, t("exporting"));
  logProcess(t("exportingTracks"));

  try {
    const active = state.stems.filter((stem) => stem.active).map((stem) => stem.id || stem.name);
    const response = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jobId: state.jobId,
        stems: active,
        bass: state.bassLevel,
        treble: state.trebleLevel,
      }),
    });
    const data = await response.json();
    updateTools(data.tools);
    if (response.status === 424 && await ensureToolsReady()) {
      return exportMix();
    }
    if (!response.ok) throw new Error(data.details || data.error || t("exportFailed"));

    await saveExport(data.url, data.filename);
    log(t("exportDownloaded"), "success");
  } catch (error) {
    log(error.message, "error");
  } finally {
    setBusy(els.exportBtn, false);
    els.exportBtn.textContent = t("exportMp3");
  }
}

async function saveExport(url, filename) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(t("couldNotDownload"));
  const blob = await response.blob();

  if ("showSaveFilePicker" in window) {
    const handle = await window.showSaveFilePicker({
      suggestedName: filename,
      types: [
        {
          description: "MP3 audio",
          accept: { "audio/mpeg": [".mp3"] },
        },
      ],
    });
    const writable = await handle.createWritable();
    await writable.write(blob);
    await writable.close();
    return;
  }

  downloadFile(URL.createObjectURL(blob), filename);
}

function downloadFile(url, filename) {
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function ensureAudioNode(audio) {
  if (!audio) return null;
  if (!visualizer.context) {
    const AudioApi = window.AudioContext || window.webkitAudioContext;
    if (!AudioApi) return null;
    visualizer.context = new AudioApi();
  }
  if (visualizer.context.state === "suspended") {
    visualizer.context.resume().catch(() => {});
  }
  const existing = visualizer.nodes.get(audio);
  if (existing) return existing;

  try {
    const analyser = visualizer.context.createAnalyser();
    analyser.fftSize = 1024;
    analyser.smoothingTimeConstant = 0.72;
    const source = visualizer.context.createMediaElementSource(audio);
    const bassFilter = visualizer.context.createBiquadFilter();
    bassFilter.type = "lowshelf";
    bassFilter.frequency.value = 160;
    bassFilter.gain.value = state.bassLevel;
    const trebleFilter = visualizer.context.createBiquadFilter();
    trebleFilter.type = "highshelf";
    trebleFilter.frequency.value = 4200;
    trebleFilter.gain.value = state.trebleLevel;
    const gainNode = visualizer.context.createGain();
    gainNode.gain.value = audio === els.sourcePlayer ? state.masterVolume : 0;
    const data = new Uint8Array(analyser.frequencyBinCount);
    source.connect(bassFilter);
    bassFilter.connect(trebleFilter);
    trebleFilter.connect(gainNode);
    gainNode.connect(analyser);
    analyser.connect(visualizer.context.destination);
    const node = { analyser, audio, bassFilter, data, gainNode, source, trebleFilter };
    visualizer.nodes.set(audio, node);
    applyPreviewGain();
    return node;
  } catch {
    return null;
  }
}

function stemSignalPeak(audio) {
  const node = ensureAudioNode(audio);
  if (!node) return 0;
  node.analyser.getByteFrequencyData(node.data);
  let peak = 0;
  for (const value of node.data) {
    if (value > peak) peak = value;
  }
  return peak;
}

function playerIsAudible({ stem, audio }) {
  const gain = visualizer.nodes.get(audio)?.gainNode?.gain.value ?? 0;
  if (!isStemActive(stem) || audio.paused || audio.ended || audio.muted || gain <= 0) {
    return false;
  }
  return stemSignalPeak(audio) >= playedStemPeakThreshold;
}

function updatePlayedStemHighlights() {
  for (const player of state.players) {
    player.card?.classList.toggle("playingStem", playerIsAudible(player));
  }
}

function startSpectrum() {
  if (visualizer.frame) return;
  drawSpectrum();
}

function drawSpectrum() {
  const canvas = els.spectrumCanvas;
  const activeAudios = [els.sourcePlayer, ...state.players.map(({ audio }) => audio)].filter((audio) => !audio.paused);
  const nodes = activeAudios.map((audio) => ensureAudioNode(audio)).filter(Boolean);
  const active = nodes.length > 0;

  drawSpectrumCanvas(canvas, mixFrequencyData(nodes), active);
  updatePlayedStemHighlights();
  updateSeekControl();

  if (active) {
    visualizer.frame = requestAnimationFrame(drawSpectrum);
  } else {
    visualizer.frame = 0;
  }
}

function mixFrequencyData(nodes) {
  if (!nodes.length) return null;
  const length = nodes[0].data.length;
  if (!visualizer.mixData || visualizer.mixData.length !== length) {
    visualizer.mixData = new Uint8Array(length);
  }
  visualizer.mixData.fill(0);
  for (const node of nodes) {
    node.analyser.getByteFrequencyData(node.data);
    for (let index = 0; index < length; index += 1) {
      visualizer.mixData[index] = Math.max(visualizer.mixData[index], node.data[index]);
    }
  }
  return visualizer.mixData;
}

function drawSpectrumCanvas(canvas, frequencyData, active) {
  const context = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  context.clearRect(0, 0, width, height);
  context.fillStyle = "#11191d";
  context.fillRect(0, 0, width, height);

  if (!active || !frequencyData) {
    context.fillStyle = "rgba(248, 251, 249, 0.18)";
    const centerY = Math.round(height * 0.5);
    for (let x = 0; x < width; x += 18) {
      context.fillRect(x, centerY, 8, 2);
    }
    return;
  }

  const bars = width > 900 ? 80 : 48;
  const gap = width > 600 ? 3 : 2;
  const barWidth = Math.max(2, (width - gap * bars) / bars);
  const usableBins = Math.floor(frequencyData.length * 0.72);

  for (let index = 0; index < bars; index += 1) {
    const start = Math.floor((index / bars) ** 1.35 * usableBins);
    const end = Math.max(start + 1, Math.floor(((index + 1) / bars) ** 1.35 * usableBins));
    let peak = 0;
    for (let bin = start; bin < end; bin += 1) {
      peak = Math.max(peak, frequencyData[bin] || 0);
    }
    const value = Math.min(1, Math.max(0.015, peak / 255));
    const barHeight = Math.max(3, value * (height - 16));
    const x = index * (barWidth + gap);
    const y = height - barHeight;
    const hue = 178 + value * 45;
    context.fillStyle = `hsl(${hue}, 72%, ${42 + value * 28}%)`;
    context.fillRect(x, y, barWidth, barHeight);
  }
}

els.chooseBtn.addEventListener("click", () => els.fileInput.click());
els.startAppBtn?.addEventListener("click", () => {
  els.splash?.classList.add("hidden");
});

els.fileInput.addEventListener("change", () => {
  const file = els.fileInput.files[0];
  if (file) uploadFile(file).catch((error) => log(error.message, "error"));
});

for (const event of ["dragenter", "dragover"]) {
  els.dropzone.addEventListener(event, (evt) => {
    evt.preventDefault();
    els.dropzone.classList.add("dragging");
  });
}

for (const event of ["dragleave", "drop"]) {
  els.dropzone.addEventListener(event, (evt) => {
    evt.preventDefault();
    els.dropzone.classList.remove("dragging");
  });
}

els.dropzone.addEventListener("drop", (evt) => {
  const file = evt.dataTransfer.files[0];
  if (file) uploadFile(file).catch((error) => log(error.message, "error"));
});

els.separateBtn.addEventListener("click", separate);
els.exportBtn.addEventListener("click", exportMix);
els.exitBtn.addEventListener("click", () => exitApplication());
els.uploadList.addEventListener("click", selectUploadFromList);
els.playMixBtn.addEventListener("click", playMix);
els.pauseBtn.addEventListener("click", () => togglePause().catch((error) => log(error.message, "error")));
els.stopMixBtn.addEventListener("click", stopMix);
els.rewindBtn?.addEventListener("click", () => rewindPlayback());
els.loopBtn?.addEventListener("click", toggleLoop);
els.volumeControl?.addEventListener("input", () => {
  setMasterVolume(Number(els.volumeControl.value) / 100);
});
els.bassControl?.addEventListener("input", () => {
  setToneLevel("bass", els.bassControl.value);
});
els.trebleControl?.addEventListener("input", () => {
  setToneLevel("treble", els.trebleControl.value);
});
els.seekControl?.addEventListener("pointerdown", () => {
  state.seeking = true;
});
els.seekControl?.addEventListener("input", () => {
  state.seeking = true;
  updateSeekControl();
  seekTo(els.seekControl.value);
});
els.seekControl?.addEventListener("change", () => {
  seekTo(els.seekControl.value);
  state.seeking = false;
  updateSeekControl();
});
els.seekControl?.addEventListener("pointerup", () => {
  state.seeking = false;
  updateSeekControl();
});
els.sourcePlayer.addEventListener("play", () => prepareAudioOutput(els.sourcePlayer));
els.sourcePlayer.addEventListener("play", startSpectrum);
els.sourcePlayer.addEventListener("play", startChordTracking);
els.sourcePlayer.addEventListener("play", updatePauseButton);
els.sourcePlayer.addEventListener("playing", updatePauseButton);
els.sourcePlayer.addEventListener("timeupdate", updateCurrentChord);
els.sourcePlayer.addEventListener("timeupdate", updatePauseButton);
els.sourcePlayer.addEventListener("timeupdate", updateSeekControl);
els.sourcePlayer.addEventListener("loadedmetadata", updateSeekControl);
els.sourcePlayer.addEventListener("seeked", updateCurrentChord);
els.sourcePlayer.addEventListener("seeked", updatePauseButton);
els.sourcePlayer.addEventListener("seeked", updateSeekControl);
els.sourcePlayer.addEventListener("pause", () => {
  updateCurrentChord();
  updatePauseButton();
  updateSeekControl();
});
els.sourcePlayer.addEventListener("ended", () => {
  if (state.loopEnabled) {
    els.sourcePlayer.currentTime = 0;
    prepareAudioOutput(els.sourcePlayer);
    els.sourcePlayer.play().catch((error) => logAudioPlayError(els.sourcePlayer, error));
    startSpectrum();
    startChordTracking();
  }
  updateCurrentChord();
  updatePauseButton();
  updateSeekControl();
});
els.clearUploadsBtn.addEventListener("click", () => clearUploads().catch((error) => log(error.message, "error")));
els.languageSelect.addEventListener("change", () => {
  currentLanguage = els.languageSelect.value;
  applyLanguage();
});
els.modelSelect.addEventListener("change", () => {
  if (!state.jobId || state.analysisRunning) return;
  separate().catch((error) => log(error.message, "error"));
});

buildPianoKeyboard();
setMasterVolume(state.masterVolume);
setToneLevel("bass", state.bassLevel);
setToneLevel("treble", state.trebleLevel);
updateLoopButton();
updateSeekControl();
applyLanguage();
getStatus().catch(() => log(t("couldNotReadStatus"), "error"));
startStatusPolling();
loadJobs().catch((error) => log(error.message, "error"));
