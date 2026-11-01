#!/usr/bin/env bash
# Корректная остановка сервера POL: SIGTERM -> сохранение мира -> выход.
#
# POL по SIGTERM/SIGINT (и по Ctrl+C в терминале) завершает работу штатно и
# пишет server/data/*.txt. Ждать нужно до закрытия порта 2593, иначе сейв
# может остаться недописанным.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${UO_PORT:-2593}"
TIMEOUT="${UO_STOP_TIMEOUT:-60}"

if systemctl --user is-active --quiet uo-shard 2>/dev/null; then
	service="yes"
else
	service="no"
fi

pids="$(pgrep -x pol || true)"

if [[ -z "$pids" && "$service" == "no" ]]; then
	echo "Сервер не запущен."
	exit 0
fi

if [[ "$service" == "yes" ]]; then
	echo "Останавливаю systemd-сервис uo-shard..."
	systemctl --user stop uo-shard.service
else
	echo "Останавливаю процесс pol (PID: $pids)..."
	# shellcheck disable=SC2086
	kill -TERM $pids
fi

waited=0
while (( waited < TIMEOUT )); do
	if ! pgrep -x pol >/dev/null 2>&1 && ! (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then
		echo "Сервер остановлен, мир сохранён."
		exit 0
	fi
	sleep 1
	waited=$((waited + 1))
done

echo "ОШИБКА: сервер не завершился за ${TIMEOUT}с. Проверь logs/pol.log." >&2
exit 1
