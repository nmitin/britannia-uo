# Передача состояния (2026-11-01, сессия 2)

Короткая точка входа для новой сессии. Полная история — в `docs/STATUS.md`.

## Репозиторий

- GitHub: https://github.com/nmitin/britannia-uo
- Ветка: `master`
- Последний коммит на момент передачи: см. `git log -1`
- `src/`, `client/`, `clientapp/`, `server/data/`, `server/realm/`,
  скомпилированные `.ecl` — не в git.

## Что уже работает

- POL 100.2.0, мир Британия 7168×4096, ClassicUO подключается.
- Русские серверные сообщения, `Cliloc.rus`.
- **Двери:** 2078 динамических дверей, `.worlddoors status`.
- **Декор мира:** 26 584 предмета обстановки (лавки, таверны, дома, доки,
  светильники, вывески) из `decoratefacets`, `.worlddecor status`.
  Генератор — `tools/import_worlddecor.py` -> `config/worlddecor.cfg`.
- **Спавн:** 15 регионов из WoD (`wod_7...wod_155`), плюс штатные 108 регионов.
- **Телепорты:** 732 dungeon-телепорта, `.worldteleporters status`.
- **Гварды:** 117 guard-постов, `.worldguards status`.
- **Торговцы/банкиры:** 230 merchant-узлов, `.worldmerchants status`.
- **Особые NPC:** 27 узлов из WoD (11 лекарей, 4 стейблмастера, 12 капитанов)
  + 172 бродячих лекаря, `.worldspecials status`.
- **Капитаны кораблей:** паромы между 12 городами — "sail"/"плыви" у капитана
  у дока, 100–500 gp. Меню — гумп (кириллица через UTF-16: пакет 0xDD),
  игрок плывёт на настоящем корабле-пароме (LargeBoat 0x11010) в открытом
  море `2398,1760` (список стоянок — `Moorings()` в `misc/sailto`),
  пакет `pkg/multis/ferry`. Все 12 городов, включая Скара Бре
  (капитан Miles, `663,2225,-3`), имеют капитана.
- В сейве ~2720 NPC; торговцы видимы, контейнеры `ShopSell/ShopeResale/ShopBuy`
  создаются (`vendorbag` включён в `config/itemdesc.cfg`).
- **Тестовый игрок:** аккаунт `drovosek` / `drovosek`, персонаж `Drovosek`
  (дровосек: Lumberjacking 100, Carpentry 70, Tinkering 30, 500 gp в банке,
  топорик и пила). Аккаунт создаётся на старте, набор выдаётся при входе —
  `scripts/include/testplayers.inc` (конфиг `config/testplayers.cfg`), один
  раз: CProp `TestPlayerPrepared`. Править конфиг → поднять `TP_VERSION`.
- **Остановка сервера:** `./scripts/stop-server.sh` (SIGTERM → сохранение
  мира → выход), Ctrl+C в терминале сервера или `systemctl --user stop uo-shard`.
- **Вода:** плавать нельзя. Игрок в воде выбирается командой `.stuck`
  (player-команда, кулдаун 30 с, ищет сушу/пирс). Высадка капитана тоже
  фильтруется (`Landable()` в `misc/sailto` и `.stuck`).
- **Логи:** `animXlate.cfg` добавлен в `server/config/` (иначе warning на
  каждое bow/salute), отладочные `Print()` из `mainHitScript` убраны.

## Быстрый запуск и проверка

```bash
cd /projects/uo
./scripts/run-server.sh
./scripts/run-client.sh
```

В игре (персонаж должен иметь `CmdLevel admin`):

```
.worlddoors status
.worlddecor status
.worldteleporters status
.worldguards status
.worldmerchants status
.worldspecials status
```

Ожидаемо: 2078 / 26 584 / 732 / 117 / 230 / 27 узлов + 172 лекаря.

## Важные нюансы

- **Сервер останавливать перед миграцией данных** — он держит мир в памяти.
- Если у персонажа не работают GM-команды, в `server/data/pcs.txt` нет
  `CmdLevel`; исправить: `python3 tools/set_cmdlevel.py --name TestAdmin2 --level admin`
  (сервер должен быть остановлен).
- `.myform` из seer-пакета иногда unknown; есть `.normalform` — воскрешает
  и возвращает человеческое тело.
- `server/data` и `server/realm` не в git; бэкапы лежат в `backups/`.
- SSH в песочнице: системный конфиг периодически ломается, для git использовать
  разово `GIT_SSH_COMMAND='ssh -F ~/.ssh/config'`.
- Декор мира: `config/worlddecor.cfg` — сгенерированный файл (3,7 МБ),
  руками не править. После перегенерации поднять `WORLDDECOR_DATA_VERSION`
  в `scripts/include/worlddecor.inc`, иначе набор не пересоберётся.
  Мировые предметы из `src/WorldOfDream/data/items.txt` для декора не
  годятся: это сейв живого шарда (двери, трупы, лут, мунгейты), а не
  обстановка.
- Активные конфиги спавна: `pkg/systems/spawnSystem/config/setup-britannia.cfg`
  и `defaultGroups.cfg`, а **не** `config/spawnregions.cfg`.
- `WorldOfDream` — источник данных, не drop-in: POL 098, карта 6144×4096.
- **Не запускать `.seednodes`** — без дедупликации засеет дубли merchant-узлов;
  бродячие лекари уже засеяны через `WSSeedHealers()` (флаг
  `WorldSpecials.HealersSeeded`), поддерживаются `verifySpecialNPCs`.

## Известные хвосты

- `wod_155` иногда пишет `Unable to get coords in region wod_155 for spawning` —
  подрезать/поправить регион.
- Не все группы WoD перенесены: `deceitlevel_*`, `dungeoncrap`, `shabooli`,
  `bucdens`, `dracos`, `snoworcs`, `windtown` и др. требуют маппинга шаблонов.
- Клиентский шрифт чата увеличен до индекса 3 в профилях; это не в git.

## Следующие шаги

1. Квесты и особые точки.
2. Починить три merchant-якоря (`2874,662`, `3687,2253`, `3704,2248`):
   правка `nodes.xml` + подъём `WM_VERSION`, иначе три строки
   `Unable to create npc` при каждом старте.
