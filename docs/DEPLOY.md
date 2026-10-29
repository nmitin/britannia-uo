# Развёртывание шарда

## 1. Подготовка данных

- Убедитесь, что в `client/` лежат файлы клиента UO (MUL/UOP), а `server/realm/`
  собран через `./scripts/rebuild-world.sh`.
- Проверьте `server/pol.cfg`: `UoDataFileRoot=../client`, порт и веб-сервер.
- Проверьте `server/config/servers.cfg`: имя и IP сервера, порт `2593`.

## 2. Безопасность (обязательно перед публичным запуском)

1. Смените пароль учётной записи `admin` в `server/data/accounts.txt`.
   Пароль хранится в виде хеша; проще всего задать новый через клиент
   командой смены пароля или пересоздать аккаунт.
2. Удалите тестовых персонажей из `server/data/pcs.txt` (сейчас оставлен
   только `TestAdmin2`, уровень player).
3. Проверьте `DefaultCmdLevel` у аккаунтов: для игроков — `player`,
   для администраторов — `admin`, не `test`.
4. Закройте веб-сервер POL (порт 5006) от внешней сети:
   `WebServerLocalOnly=1` или настройте `WebServerPassword`.
5. Настройте firewall: наружу нужен только `2593/tcp` (и `5006/tcp`,
   если веб-консоль действительно нужна снаружи).

## 3. Автозапуск (systemd)

Скрипт `scripts/install-systemd.sh` создаёт пользовательский сервис
`uo-shard` с автоперезапуском и логами в `logs/`.

Внутри sandbox-сессии DSH пользовательская шина systemd недоступна,
поэтому устанавливать сервис нужно в обычном терминале:

```bash
./scripts/install-systemd.sh
systemctl --user status uo-shard
journalctl --user -u uo-shard -f
```

Чтобы сервис работал после выхода из сеанса:

```bash
loginctl enable-linger "$USER"
```

## 4. Резервные копии

```bash
./scripts/backup.sh
```

Хранятся последние 14 архивов в `backups/`. Рекомендуется добавить запуск
по cron/systemd timer, например раз в час.

## 5. Клиент для игроков

- Клиент: ClassicUO (Linux/Windows) + файлы UO.
- В `settings.json` у игрока: `ip`, `port` (2593), `lang: "rus"`.
- Файл `Cliloc.rus` положить в папку клиента.
- Для кириллицы в гумпах/сообщениях ничего дополнительно не нужно.

## 6. Обновление контента

```bash
./scripts/compile-scripts.sh     # перекомпилировать скрипты
systemctl --user restart uo-shard
```

После правок itemdesc/конфигов обязателен перезапуск сервера.
