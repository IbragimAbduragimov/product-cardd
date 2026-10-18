# Shorts Studio

Монтаж вертикальных роликов (Reels / TikTok / YouTube Shorts) на HyperFrames: русские субтитры по словам, анимации, переходы, вставки, экспорт в MP4.

## Структура

| Папка        | Что лежит                                                         |
| ------------ | ----------------------------------------------------------------- |
| `input/`     | Исходные видео пользователя. **Только чтение** — никогда не менять и не удалять. |
| `music/`     | Фоновая музыка                                                    |
| `images/`    | Картинки, логотипы для вставок                                    |
| `broll/`     | Дополнительные видео-вставки (перебивки)                          |
| `subtitles/` | Экспорт субтитров: `<имя>.srt`                                    |
| `projects/`  | Один HyperFrames-проект на ролик: `projects/<имя>/`               |
| `output/`    | Готовые MP4                                                       |
| `templates/selftest/` | Тестовая композиция для проверки окружения               |

## Правило языка (обязательно)

Речь в роликах — **русская**. Навыки HyperFrames по умолчанию используют `small.en`, который **переводит** русскую речь на английский. Поэтому при любой транскрибации, в том числе внутри навыков `/embedded-captions` и `/talking-head-recut`, всегда передавай:

```
--model small --language ru
```

Для шумного звука или речи на фоне музыки: `--model medium --language ru`. Модели `*.en` не использовать никогда.

Движок распознавания — встроенная интеграция HyperFrames с whisper.cpp. На Windows путь к `whisper-cli.exe` задан в переменной `HYPERFRAMES_WHISPER_PATH` (её ставит `scripts/setup-windows.ps1`). Другие реализации Whisper не ставить.

## Процесс: «смонтируй input/<файл>»

1. **Разбор исходника:** `ffprobe -v error -show_entries stream=codec_type,width,height:format=duration -of compact input/<файл>`. Имя проекта `<имя>` — латиницей, по имени файла, без перезаписи: если `projects/<имя>` уже есть, добавь суффикс `-2`, `-3`…
2. **Проект + транскрипция одной командой:**
   ```
   hyperframes init projects/<имя> --video input/<файл> --resolution portrait --model small --language ru --non-interactive
   ```
   Видео копируется в `projects/<имя>/source.mp4`, слова с таймингами — в `projects/<имя>/transcript.json`.
3. **Проверка транскрипта:** прочитай `transcript.json`, убедись, что текст русский и осмысленный. Если нет — перезапусти с `--model medium --language ru`:
   `hyperframes transcribe projects/<имя>/source.mp4 -d projects/<имя> --model medium --language ru`
4. **Субтитры в файл:** `hyperframes transcribe projects/<имя>/transcript.json --to srt -o subtitles/<имя>.srt`
5. **Монтаж — через навыки** (начни с `/hyperframes`, он выберет сценарий):
   - только стилизованные субтитры → `/embedded-captions`;
   - субтитры + вставки, заголовки, плашки, анимации → `/talking-head-recut` (формат 9:16);
   - собственный монтаж из нескольких клипов, музыки, картинок → `/general-video`.
   Материалы для вставок бери из `music/`, `images/`, `broll/`. Холст — 1080×1920. Субтитры не должны перекрывать лицо и интерфейс платформ (снизу ~600 px и справа ~150 px заняты кнопками).
6. **Проверка:** `hyperframes check projects/<имя>` — исправить все ошибки и предупреждения layout.
7. **Рендер:** `hyperframes render projects/<имя> -o output/<имя>.mp4 --quality high`. Если файл уже есть — `output/<имя>-v2.mp4` и т. д., не перезаписывать.
8. **Проверка результата:** `ffprobe` (h264, 1080×1920, длительность ≈ исходнику) и `ffmpeg -v error -i output/<имя>.mp4 -f null -` без ошибок. Сообщи пользователю путь к MP4 и к SRT.

## Проверка окружения

```
npm run selftest            # рендер templates/selftest → output/selftest.mp4
hyperframes doctor          # зависимости HyperFrames
```
