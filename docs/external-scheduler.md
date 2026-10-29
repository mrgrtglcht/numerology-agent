# внешний запуск через cron-job.org

сервис запускает workflow на github через авторизованный запрос. сам контент, секреты postwire и telegram остаются на github. успешный HTTP-ответ означает только принятие команды; итог проверяется в Actions и postwire.

## 1. ключ github

создать fine-grained personal access token: https://github.com/settings/personal-access-tokens/new

- имя: numerology-scheduler.
- resource owner: mrgrtglcht.
- срок: 90 дней; перед окончанием заменить ключ в cron-job.org.
- repository access: only select repositories → numerology-agent.
- repository permissions → actions: read and write.
- metadata: read-only добавляется автоматически.
- остальные разрешения не нужны.

ключ вставляется только в заголовок Authorization в cron-job.org. не отправлять его в чат, не сохранять в репозитории.

## 2. задача cron-job.org

создать задачу, сначала отключённую, чтобы настроить поля.

название: numerology-agent queue check
URL:
https://api.github.com/repos/mrgrtglcht/numerology-agent/actions/workflows/cloud.yml/dispatches

расписание: каждый час, на 17-й минуте.
метод: POST.
заголовки:
- Authorization: Bearer ВАШ_КЛЮЧ
- Accept: application/vnd.github+json
- Content-Type: application/json
- X-GitHub-Api-Version: 2026-03-10

тело запроса для обычной проверки очереди:
```json
{"ref":"main","inputs":{"mode":"scheduled"}}
```

это не команда publish-now: агент сверит журнал, очередь, лимиты и сохранённую подготовку. неопределённые отправки повторно не отправляются. цель — три будущих тиктока; подготовка идёт по одному материалу за запуск и с существующим дневным ограничителем.

для первого теста подключения без подготовки и отправок:
```json
{"ref":"main","inputs":{"mode":"check"}}
```

## 3. проверка и включение

1. выполнить тест с mode=check. HTTP 200 или 204 означает, что github принял команду.
2. в Actions найти запуск workflow_dispatch и убедиться, что проверка подключений завершилась успешно.
3. заменить тело на mode=scheduled, включить задачу и дождаться именно автоматического запуска.
4. проверить результат workflow и фактический новый пост в postwire, а не только ответ cron-job.org.
5. включить уведомления cron-job.org об ошибках и отключении задачи. ошибки после принятия команды видны в github actions, а не в HTTP-статусе cron-job.org.

HTTP 401: неверный или истёкший ключ.
HTTP 403: недостаточно разрешений или ограничение доступа.
HTTP 404: неправильный адрес или доступ к репозиторию.
HTTP 422: неверная ветка или inputs.

встроенное расписание github остаётся резервным. оба источника используют один workflow, общую блокировку и журнал отправок.

эта задача запускает tiktok и штатную проверку telegram по локальному расписанию. отдельный Pinterest workflow этим запросом не запускается.
