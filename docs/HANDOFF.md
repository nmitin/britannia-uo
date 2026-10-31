# Передача состояния (2026-10-31)

Короткая точка входа для новой сессии. Полная история — в `docs/STATUS.md`.

## Репозиторий

- GitHub: https://github.com/nmitin/britannia-uo
- Ветка: `master`
- Последний коммит на момент передачи: `f515d62`
- `src/`, `client/`, `clientapp/`, `server/data/`, `server/realm/`,
  скомпилированные `.ecl` — не в git.

## Что уже работает

- POL 100.2.0, мир Британия 7168×4096, ClassicUO подключается.
- Русские серверные сообщения, `Cliloc.rus`.
- **Двери:** 2078 динамических дверей, `.worlddoors status`.
- **Спавн:** 15 регионов из WoD (`wod_7...wod_155`), плюс штатные 108 регионов.
- **Телепорты:** 732 dungeon-телепорта, `.worldteleporters status`.
- **Гварды:** 117 guard-постов, `.worldguards status`.
- **Торговцы/банкиры:** 230 merchant-узлов, `.worldmerchants status`.
- В сейве ~2720 NPC; торговцы видимы, контейнеры `ShopSell/ShopeResale/ShopBuy`
  создаются (`vendorbag` включён в `config/itemdesc.cfg`).

## Быстрый запуск и проверка

```bash
cd /projects/uo
./scripts/run-server.sh
./scripts/run-client.sh
```

В игре (персонаж должен иметь `CmdLevel admin`):

```
.worlddoors status
.worldteleporters status
.worldguards status
.worldmerchants status
```

Ожидаемо: 2078 / 732 / 117 / 230.

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
- Активные конфиги спавна: `pkg/systems/spawnSystem/config/setup-britannia.cfg`
  и `defaultGroups.cfg`, а **не** `config/spawnregions.cfg`.
- `WorldOfDream` — источник данных, не drop-in: POL 098, карта 6144×4096.

## Известные хвосты

- `wod_155` иногда пишет `Unable to get coords in region wod_155 for spawning` —
  подрезать/поправить регион.
- Не все группы WoD перенесены: `deceitlevel_*`, `dungeoncrap`, `shabooli`,
  `bucdens`, `dracos`, `snoworcs`, `windtown` и др. требуют маппинга шаблонов.
- Клиентский шрифт чата увеличен до индекса 3 в профилях; это не в git.

## Следующие шаги

1. Специальные NPC: бродячие лекари, town healer, stablemaster.
2. Мировые предметы/декор из WoD (осторожно, там есть мусор и дубли).
3. Квесты и особые точки.
4. Проверить ассортимент/рестокинг торговцев в Британии и Тринсике.
