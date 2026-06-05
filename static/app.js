const state = {
  jobId: "",
  file: null,
  filename: "",
  sourceUrl: "",
  stems: [],
  players: [],
  chords: [],
  mixPlaying: false,
  mixStartedAt: 0,
  jobs: [],
  tools: {},
};

const els = {
  dropzone: document.querySelector("#dropzone"),
  fileInput: document.querySelector("#fileInput"),
  chooseBtn: document.querySelector("#chooseBtn"),
  sourcePlayer: document.querySelector("#sourcePlayer"),
  splash: document.querySelector("#splash"),
  startAppBtn: document.querySelector("#startAppBtn"),
  separateBtn: document.querySelector("#separateBtn"),
  exportBtn: document.querySelector("#exportBtn"),
  playMixBtn: document.querySelector("#playMixBtn"),
  stopMixBtn: document.querySelector("#stopMixBtn"),
  stems: document.querySelector("#stems"),
  uploadList: document.querySelector("#uploadList"),
  spectrumCanvas: document.querySelector("#spectrumCanvas"),
  chordTimeline: document.querySelector("#chordTimeline"),
  currentChord: document.querySelector("#currentChord"),
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
    playSelected: "Play Selected",
    stop: "Stop",
    stemModel: "Stem model",
    model6: "6 stems: vocals, drums, bass, guitar, piano, other",
    model4: "4 stems: vocals, drums, bass, other",
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
    separationFailed: "Separation failed.",
    foundTracks: "Found {count} tracks: {tracks}.",
    select: "Select",
    exporting: "Exporting...",
    exportingTracks: "Exporting selected tracks to MP3...",
    exportFailed: "Export failed.",
    exportDownloaded: "MP3 export downloaded.",
    couldNotDownload: "Could not download exported MP3.",
    couldNotReadStatus: "Could not read tool status.",
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
  ffmpeg: "FFmpeg",
  codecs: "Codecs",
  chords: "Chords",
};

let currentLanguage = localStorage.getItem("detrace-language") || "en";

const visualizer = {
  context: null,
  nodes: new WeakMap(),
  frame: 0,
  chordFrame: 0,
};

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
  localStorage.setItem("detrace-language", currentLanguage);
}

function setAudioSource(audio, src) {
  audio.pause();
  audio.src = src;
  audio.load();
  audio.addEventListener("play", () => {
    ensureAudioNode(audio);
    startSpectrum();
    startChordTracking();
  }, { once: true });
}

function log(message, type = "") {
  const item = document.createElement("li");
  item.textContent = message;
  if (type) item.className = type;
  els.log.prepend(item);
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
}

async function getStatus() {
  const response = await fetch("/api/status");
  const data = await response.json();
  updateTools(data.tools);
  return data.tools;
}

function toolsReady(tools = {}) {
  return Boolean(tools.demucs && tools.ffmpeg && tools.codecs && tools.chords);
}

async function ensureToolsReady() {
  const tools = await getStatus();
  if (toolsReady(tools)) return true;
  const missing = Object.entries(toolLabels)
    .filter(([key]) => !tools[key])
    .map(([, label]) => label)
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

  stopMix();
  const response = await fetch("/api/jobs", { method: "DELETE" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || t("couldNotClearUploads"));

  state.jobId = "";
  state.file = null;
  state.filename = "";
  state.sourceUrl = "";
  state.stems = [];
  state.chords = [];
  state.players = [];
  state.jobs = [];
  setAudioSource(els.sourcePlayer, "");
  els.stems.innerHTML = "";
  els.separateBtn.disabled = true;
  els.exportBtn.disabled = true;
  els.playMixBtn.disabled = true;
  els.stopMixBtn.disabled = true;
  updateTools(data.tools);
  renderJobs();
  renderChords();
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
    button.classList.toggle("active", job.jobId === state.jobId);

    const title = document.createElement("span");
    title.className = "uploadName";
    title.textContent = job.filename;

    const meta = document.createElement("span");
    meta.className = "uploadMeta";
    meta.textContent = job.analyzed ? t("tracksFound", { count: job.stems.length }) : t("notAnalyzed");

    button.append(title, meta);
    button.addEventListener("click", () => selectJob(job));
    els.uploadList.append(button);
  }
}

function loadJobIntoView(job) {
  stopMix();
  state.jobId = job.jobId;
  state.filename = job.filename;
  state.sourceUrl = job.sourceUrl;
  state.file = null;
  state.stems = (job.stems || []).map((stem) => ({ ...stem, active: true }));
  state.chords = [];
  setAudioSource(els.sourcePlayer, job.sourceUrl);
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
    log(t("loaded", { filename: data.job.filename }), "success");
  } catch (error) {
    log(error.message, "error");
  }
}

async function uploadFile(file) {
  state.file = file;
  state.filename = file.name;
  state.stems = [];
  state.chords = [];
  state.players = [];
  els.stems.innerHTML = "";
  renderChords();
  els.stems.setAttribute("aria-busy", "true");
  setAudioSource(els.sourcePlayer, URL.createObjectURL(file));
  els.separateBtn.disabled = true;
  els.exportBtn.disabled = true;
  els.playMixBtn.disabled = true;
  els.stopMixBtn.disabled = true;
  log(t("uploading", { filename: file.name }));

  const response = await fetch("/api/upload", {
    method: "POST",
    headers: { "X-Filename": file.name },
    body: file,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || t("uploadFailed"));

  state.jobId = data.jobId;
  state.filename = data.filename;
  state.sourceUrl = data.sourceUrl;
  setAudioSource(els.sourcePlayer, data.sourceUrl);
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
  const model = els.modelSelect.value;
  setBusy(els.separateBtn, true, t("analyzing"));
  els.exportBtn.disabled = true;
  els.playMixBtn.disabled = true;
  els.stopMixBtn.disabled = true;
  els.stems.innerHTML = "";
  state.chords = [];
  renderChords();
  els.stems.setAttribute("aria-busy", "true");
  log(t("analyzingWithModel", { model }));
  log(t("detectingChordsLog"));

  try {
    const [stemResult, chordResult] = await Promise.all([
      postJson("/api/separate", { jobId: state.jobId, model }),
      postJson("/api/chords", { jobId: state.jobId }),
    ]);
    updateTools({ ...(stemResult.data.tools || {}), ...(chordResult.data.tools || {}) });

    if ((stemResult.response.status === 424 || chordResult.response.status === 424) && await ensureToolsReady()) {
      return separate();
    }
    if (!stemResult.response.ok) {
      throw new Error(stemResult.data.details || stemResult.data.error || t("separationFailed"));
    }

    state.stems = stemResult.data.stems.map((stem) => ({ ...stem, active: true }));
    renderStems();
    els.exportBtn.disabled = false;
    els.playMixBtn.disabled = false;
    els.stopMixBtn.disabled = false;

    if (chordResult.response.ok) {
      state.chords = chordResult.data.chords || [];
      renderChords();
      log(state.chords.length ? t("chordsReady", { count: state.chords.length }) : t("noChordsFound"), "success");
    } else {
      renderChords();
      log(chordResult.data.details || chordResult.data.error || t("chordDetectionFailed"), "error");
    }

    await loadJobs();
    log(t("foundTracks", { count: state.stems.length, tracks: state.stems.map((stem) => stem.name).join(", ") }), "success");
  } catch (error) {
    log(error.message, "error");
  } finally {
    setBusy(els.separateBtn, false);
    els.separateBtn.textContent = t("analyzeAgain");
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
    checkbox.addEventListener("change", () => {
      stem.active = checkbox.checked;
      syncPlayers();
    });
    toggle.append(checkbox, t("select"));

    const audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "metadata";
    setAudioSource(audio, stem.url);

    const canvas = document.createElement("canvas");
    canvas.className = "stemSpectrum";
    canvas.width = 520;
    canvas.height = 92;
    drawSpectrumCanvas(canvas, null, false);

    header.append(name, toggle);
    card.append(header, audio, canvas);
    els.stems.append(card);
    state.players.push({ stem, audio, canvas });
  }
}

function renderChords() {
  els.chordTimeline.innerHTML = "";
  els.currentChord.textContent = t("noChord");
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
  const time = state.mixPlaying ? currentMixTime() : els.sourcePlayer.currentTime || 0;
  let activeIndex = -1;
  for (let index = 0; index < state.chords.length; index += 1) {
    if (time >= state.chords[index].start) activeIndex = index;
  }
  const active = activeIndex >= 0 ? state.chords[activeIndex] : null;
  els.currentChord.textContent = active ? active.chord : t("noChord");
  for (const [index, item] of [...els.chordTimeline.querySelectorAll(".chordItem")].entries()) {
    const start = Number(item.dataset.start);
    const isActive = index === activeIndex;
    item.classList.toggle("active", isActive);
    item.classList.toggle("played", time >= start);
    item.setAttribute("aria-current", isActive ? "true" : "false");
  }
}

function startChordTracking() {
  if (visualizer.chordFrame) return;
  trackChords();
}

function trackChords() {
  updateCurrentChord();
  const sourcePlaying = !els.sourcePlayer.paused && !els.sourcePlayer.ended;
  if (sourcePlaying || state.mixPlaying) {
    visualizer.chordFrame = requestAnimationFrame(trackChords);
  } else {
    visualizer.chordFrame = 0;
  }
}

function syncPlayers() {
  const hasSelection = state.stems.some((stem) => stem.active);
  els.exportBtn.disabled = !hasSelection;
  els.playMixBtn.disabled = !hasSelection;
  els.stopMixBtn.disabled = !state.players.length;
  for (const { stem, audio } of state.players) {
    if (!stem.active && !audio.paused) {
      audio.pause();
    }
    if (stem.active && state.mixPlaying) {
      ensureAudioNode(audio);
      audio.currentTime = currentMixTime();
      audio.play().catch((error) => log(error.message, "error"));
    }
  }
}

async function playMix() {
  const activePlayers = state.players.filter(({ stem }) => stem.active);
  if (!activePlayers.length) return;
  stopMix();
  state.mixPlaying = true;
  state.mixStartedAt = performance.now();
  for (const { audio } of activePlayers) {
    ensureAudioNode(audio);
    audio.currentTime = 0;
  }
  startSpectrum();
  startChordTracking();
  await Promise.all(activePlayers.map(({ audio }) => audio.play()));
}

function stopMix() {
  for (const { audio } of state.players) {
    audio.pause();
    audio.currentTime = 0;
  }
  state.mixPlaying = false;
  state.mixStartedAt = 0;
  updateCurrentChord();
}

function currentMixTime() {
  if (!state.mixPlaying || !state.mixStartedAt) return 0;
  const elapsed = (performance.now() - state.mixStartedAt) / 1000;
  const durations = state.players
    .map(({ audio }) => audio.duration)
    .filter((duration) => Number.isFinite(duration) && duration > 0);
  if (!durations.length) return elapsed;
  return Math.min(elapsed, Math.max(...durations));
}

async function exportMix() {
  setBusy(els.exportBtn, true, t("exporting"));
  log(t("exportingTracks"));

  try {
    const active = state.stems.filter((stem) => stem.active).map((stem) => stem.name);
    const response = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jobId: state.jobId, stems: active }),
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
  if (!visualizer.context) {
    const AudioApi = window.AudioContext || window.webkitAudioContext;
    visualizer.context = new AudioApi();
  }
  if (visualizer.context.state === "suspended") {
    visualizer.context.resume();
  }
  if (!visualizer.nodes.has(audio)) {
    const analyser = visualizer.context.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.78;
    const data = new Uint8Array(analyser.frequencyBinCount);
    const source = visualizer.context.createMediaElementSource(audio);
    source.connect(analyser);
    analyser.connect(visualizer.context.destination);
    visualizer.nodes.set(audio, { source, analyser, data });
  }
  return visualizer.nodes.get(audio);
}

function startSpectrum() {
  if (visualizer.frame) return;
  drawSpectrum();
}

function drawSpectrum() {
  const canvas = els.spectrumCanvas;
  const activeAudios = [els.sourcePlayer, ...state.players.map(({ audio }) => audio)].filter((audio) => !audio.paused);
  const active = activeAudios.length > 0;
  const masterNode = activeAudios.map((audio) => visualizer.nodes.get(audio)).find(Boolean);

  drawSpectrumCanvas(canvas, masterNode, active);

  for (const { audio, canvas: stemCanvas } of state.players) {
    const node = visualizer.nodes.get(audio);
    drawSpectrumCanvas(stemCanvas, node, !audio.paused);
  }

  if (active) {
    visualizer.frame = requestAnimationFrame(drawSpectrum);
  } else {
    visualizer.frame = 0;
  }
}

function drawSpectrumCanvas(canvas, node, active) {
  const context = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  context.clearRect(0, 0, width, height);
  context.fillStyle = "#11191d";
  context.fillRect(0, 0, width, height);

  if (!node || !active) {
    context.fillStyle = "rgba(248, 251, 249, 0.18)";
    const centerY = Math.round(height * 0.5);
    for (let x = 0; x < width; x += 18) {
      context.fillRect(x, centerY, 8, 2);
    }
    return;
  }

  node.analyser.getByteFrequencyData(node.data);
  const bars = node.data.length;
  const gap = width > 600 ? 3 : 2;
  const barWidth = Math.max(2, (width - gap * bars) / bars);

  for (let index = 0; index < bars; index += 1) {
    const value = node.data[index] / 255;
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
els.playMixBtn.addEventListener("click", playMix);
els.stopMixBtn.addEventListener("click", stopMix);
els.sourcePlayer.addEventListener("play", startChordTracking);
els.sourcePlayer.addEventListener("timeupdate", updateCurrentChord);
els.sourcePlayer.addEventListener("seeked", updateCurrentChord);
els.sourcePlayer.addEventListener("pause", updateCurrentChord);
els.sourcePlayer.addEventListener("ended", updateCurrentChord);
els.clearUploadsBtn.addEventListener("click", () => clearUploads().catch((error) => log(error.message, "error")));
els.languageSelect.addEventListener("change", () => {
  currentLanguage = els.languageSelect.value;
  applyLanguage();
});

applyLanguage();
getStatus().catch(() => log(t("couldNotReadStatus"), "error"));
loadJobs().catch((error) => log(error.message, "error"));
