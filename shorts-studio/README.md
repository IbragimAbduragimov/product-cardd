# Shorts Studio

Автоматический монтаж Reels / TikTok / YouTube Shorts на [HyperFrames](https://github.com/heygen-com/hyperframes): русские субтитры по словам (whisper.cpp), анимации, переходы, вставки, экспорт в MP4 1080×1920.

## Установка на Windows

```powershell
git clone https://github.com/ibragimabduragimov/product-cardd.git
cd product-cardd\shorts-studio
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-windows.ps1
```

`-ExecutionPolicy Bypass` действует только на этот запуск и не меняет политику Windows.

Параметры:

- `-Model medium` — точнее для шумного звука (1,5 ГБ, медленнее; по умолчанию `small`, 466 МБ);
- `-ProjectDir D:\shorts-studio` — другая папка проекта (по умолчанию `%USERPROFILE%\shorts-studio`);
- `-Play` — открыть тестовый MP4 после рендера;
- `-SkipSkills` — не ставить навыки Claude Code.

Скрипт по шагам: проверяет ОС, winget, Node.js ≥ 22, npm, Git, Python, Chrome → ставит недостающее через winget (FFmpeg — `Gyan.FFmpeg`) → `npm i -g hyperframes` + `hyperframes browser ensure` → официальный релиз whisper.cpp (`ggml-org/whisper.cpp`, проверка SHA-256), `HYPERFRAMES_WHISPER_PATH`, реальная русская транскрипция → `npx skills add heygen-com/hyperframes` → копирует проект без перезаписи существующих файлов → тестовый рендер и проверка MP4 через ffprobe/ffmpeg. Уже работающие компоненты не переустанавливаются. При любой ошибке скрипт останавливается и показывает её.

## Монтаж

1. Положите видео в `%USERPROFILE%\shorts-studio\input\`.
2. В **новом** терминале: `cd %USERPROFILE%\shorts-studio` → `claude`.
3. Напишите: `смонтируй input\мое-видео.mp4` (можно добавить пожелания: стиль субтитров, музыку из `music\`, вставки из `images\` / `broll\`).

Результат: `output\<имя>.mp4` и `subtitles\<имя>.srt`. Процесс описан в [CLAUDE.md](CLAUDE.md).

Только субтитры, без Claude:

```powershell
hyperframes init projects\demo --video input\demo.mp4 --resolution portrait --model small --language ru --non-interactive
hyperframes transcribe projects\demo\transcript.json --to srt -o subtitles\demo.srt
```

Проверка окружения в любой момент: `npm run selftest`.
