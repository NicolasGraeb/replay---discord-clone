# Backend API - dokumentacja

REST API i WebSocket dla klienta „Discord‑like” (serwery, kanały tekstowe i głosowe, wiadomości, media, JWT). Poniżej: **modele danych** (pole po polu i relacje), **biblioteki**, **uwierzytelnianie** oraz **czat i realtime**.

---

## Stack i biblioteki

| Biblioteka | Zastosowanie |
|------------|----------------|
| **FastAPI** | Aplikacja HTTP, routing, dependency injection, walidacja wejścia (Pydantic), WebSocket. |
| **Uvicorn** | Serwer ASGI (uruchomienie aplikacji). |
| **SQLAlchemy 2.x** (async) | ORM: modele `Mapped` / `mapped_column`, relacje, sesje asynchroniczne. |
| **asyncpg** | Sterownik PostgreSQL pod silnik async SQLAlchemy. |
| **Pydantic v2** | Schematy API (`BaseModel`), konfiguracja pól (`Field`). |
| **python-jose** (`cryptography`) | JWT: podpis HS256, dekodowanie access/refresh. |
| **passlib[bcrypt]** | Kontekst `CryptContext` - hash i weryfikacja haseł (bcrypt). |
| **python-dotenv** / **loadenv** | Wczytanie zmiennych z `.env` (`config/envs.py`). |
| **boto3** | Klient zgodny z S3 - upload i presigned URL do MinIO (obrazy czatu, avatary). |
| **Pillow** | Przetwarzanie obrazów: kompresja czatu, pipeline avatara (WebP, crop, EXIF). |
| **pytest** / **pytest-asyncio** | Testy (grupa `dev` w `pyproject.toml`). |

Baza: **PostgreSQL** (URL w `DATABASE_URL`). Migracje startowe: `core/startup_db.py` (DDL przy starcie aplikacji).

---

## Architektura kodu (warstwy)

- **`controllers/`** - endpointy HTTP: walidacja wejścia, wywołania serwisów, odpowiedzi Pydantic, wyjątki HTTP.
- **`services/`** - logika biznesowa (transakcje przez repozytoria, reguły domenowe).
- **`repositories/`** - dostęp do bazy (CRUD, zapytania, `joinedload` tam, gdzie potrzeba).
- **`models/`** - encje SQLAlchemy (tabele, relacje, `ForeignKey`).
- **`schemas/`** - modele Pydantic dla request/response (nie zawsze 1:1 z encjami).
- **`ws/`** - WebSocket: `channel_ws.py`, `connection_manager.py`.
- **`core/`** - bezpieczeństwo JWT/hasła, S3, obrazy, zależności FastAPI (`dependencies.py`).
- **`config/`** - `database.py` (engine, sesja), `envs.py` (stałe z ENV).

---

## Modele bazy danych (SQLAlchemy)

Wszystkie tabele dziedziczą z **`Base`** (`models/base.py`). Mixin **`TimestampMixin`** dodaje pole czasowe utworzenia rekordu.

### `TimestampMixin` (`models/base.py`)

| Pole | Typ | Opis |
|------|-----|------|
| `created_at` | `datetime`, `NOT NULL`, domyślnie `now()` po stronie serwera Bazy | Moment utworzenia wiersza (UTC w praktyce operacyjnej). |

---

### `User` - tabela `users` (`models/user.py`)

| Pole | Typ / ograniczenia | Opis |
|------|-------------------|------|
| `id` | `UUID`, PK, domyślnie `uuid4` | Identyfikator użytkownika. |
| `username` | `String(60)`, `UNIQUE`, `NOT NULL`, indeks | Nazwa wyświetlana (login „społecznościowy”). |
| `email` | `String(90)`, `UNIQUE`, `NOT NULL`, indeks | Email (logowanie). |
| `hashed_password` | `String(255)`, `NOT NULL` | Hash bcrypt (nie plain text). |
| `avatar_url` | `String(500)`, nullable | Klucz obiektu w MinIO **albo** pełny URL `http(s)://` (legacy). |
| `created_at` | z `TimestampMixin` | Data rejestracji. |

**Relacje (SQLAlchemy `relationship`):**

| Relacja | Cel | `back_populates` / uwagi |
|---------|-----|---------------------------|
| `owned_servers` | lista `Server` | Serwery, których użytkownik jest **właścicielem** (`Server.owner_id` → ten `User`). `foreign_keys` wskazuje `Server.owner_id`. |
| `server_memberships` | lista `ServerMember` | Członkostwa na serwerach. **Cascade:** `all, delete-orphan` - usunięcie usera usuwa wiersze `server_members`. |
| `messages` | lista `Message` | Wiadomości użytkownika jako autor. **Cascade:** `all, delete-orphan` - usunięcie usera usuwa jego wiadomości. |
| `refresh_tokens` | lista `RefreshToken` | Tokeny odświeżania. **Cascade:** `all, delete-orphan`. |

---

### `RefreshToken` - tabela `refresh_tokens` (`models/refresh_token.py`)

Przechowuje **jti** (JWT ID) refresh tokena w celu rotacji i unieważniania.

| Pole | Typ | Opis |
|------|-----|------|
| `id` | `UUID`, PK **bez** domyślnego generatora w ORM | **Równe `jti` z payloadu JWT** - jednoznaczna identyfikacja wystawionego refresh tokena. |
| `user_id` | `UUID`, FK → `users.id`, `ON DELETE CASCADE`, indeks | Właściciel tokena. |
| `expires_at` | `datetime`, `NOT NULL` | Wygaśnięcie (w DB często naive UTC). |
| `revoked` | `Boolean`, `NOT NULL`, domyślnie `False` | Po udanym refresh lub logout - `True`; przy podejrzeniu reuse - strategia w serwisie może unieważnić wszystkie tokeny usera. |
| `created_at` | `TimestampMixin` | Moment zapisania rekordu przy `login`. |

**Relacja:** `user` → `User` (`back_populates="refresh_tokens"`).

---

### `Server` - tabela `servers` (`models/server.py`)

| Pole | Typ | Opis |
|------|-----|------|
| `id` | `UUID`, PK | Identyfikator serwera (np. w URL zaproszenia). |
| `name` | `String(100)`, `NOT NULL` | Nazwa serwera. |
| `owner_id` | `UUID`, FK → `users.id`, `ON DELETE RESTRICT`, `NOT NULL` | Właściciel - **nie można** usunąć usera, dopóki jest ownerem serwera (bez zmiany ownera). |
| `icon_url` | `String(500)`, nullable | Opcjonalna ikona (URL lub klucz - zależnie od konwencji frontu). |
| `created_at` | `TimestampMixin` | |

**Relacje:**

| Relacja | Opis |
|---------|------|
| `owner` | `User` - właściciel (`foreign_keys=[owner_id]`). |
| `members` | `ServerMember[]` - **cascade** `all, delete-orphan`: usunięcie serwera usuwa członkostwa. |
| `channels` | `Channel[]` - **cascade** `all, delete-orphan`: usunięcie serwera usuwa kanały. |

---

### `ServerMember` - tabela `server_members` (`models/server_member.py`)

Powiązanie **użytkownik ↔ serwer** z rolą. Klucz główny złożony.

| Pole | Typ | Opis |
|------|-----|------|
| `user_id` | `UUID`, PK, FK → `users.id`, `ON DELETE CASCADE` | Użytkownik. |
| `server_id` | `UUID`, PK, FK → `servers.id`, `ON DELETE CASCADE` | Serwer. |
| `role` | enum `MemberRole` (PostgreSQL `memberrole`) | `OWNER`, `ADMIN`, `MODERATOR`, `MEMBER`. |
| `joined_at` | `datetime`, `NOT NULL`, domyślnie `now()` | Dołączenie do serwera. |

**Relacje:** `user` → `User`, `server` → `Server`.

**Uwaga:** Brak `TimestampMixin` - jedyny znacznik czasu to `joined_at`.

---

### `Channel` - tabela `channels` (`models/channel.py`)

| Pole | Typ | Opis |
|------|-----|------|
| `id` | `UUID`, PK | Identyfikator kanału. |
| `name` | `String(100)`, `NOT NULL` | Nazwa (np. `general`, `chat2`). |
| `server_id` | `UUID`, FK → `servers.id`, `ON DELETE CASCADE`, `NOT NULL` | Serwer nadrzędny. |
| `type` | enum `ChannelType` (`TEXT` / `VOICE`), `NOT NULL`, domyślnie `TEXT` | Kanał tekstowy vs głosowy (logika WS i uploadów). |
| `created_at` | `TimestampMixin` | |

**Relacje:**

| Relacja | Opis |
|---------|------|
| `server` | `Server`. |
| `messages` | `Message[]` - **cascade** `all, delete-orphan`. |

---

### `Message` - tabela `messages` (`models/message.py`)

| Pole | Typ | Opis |
|------|-----|------|
| `id` | `UUID`, PK | Id wiadomości. |
| `content` | `Text`, `NOT NULL` | Treść tekstowa (również przy wiadomości tylko ze zdjęciem może być podpis / pusty string wg logiki serwisu - kontroler wymusza sensowną walidację). |
| `author_id` | `UUID`, FK → `users.id`, `ON DELETE CASCADE`, `NOT NULL` | Autor. |
| `channel_id` | `UUID`, FK → `channels.id`, `ON DELETE CASCADE`, `NOT NULL`, indeks | Kanał. |
| `image_key` | `String(512)`, nullable | Klucz obiektu w bucketcie MinIO (np. `messages/.../....webp`); brak = wiadomość bez załączonego obrazka. |
| `created_at` | `TimestampMixin` | |
| `updated_at` | `datetime`, nullable | Uzupełniane przy edycji treści (`PATCH`). |

**Indeks:** `ix_messages_channel_created` na `(channel_id, created_at)` - szybkie listowanie historii kanału.

**Relacje:** `author` → `User`, `channel` → `Channel`.

---

## Uwierzytelnianie i autoryzacja

### Hasła (`core/security.py`)

- **passlib** `CryptContext(schemes=["bcrypt"])` - `hash_password` / `verify_password`.

### JWT

- **Algorytm:** `HS256`, sekret `JWT_SECRET_KEY` (`config/envs.py`).
- **Access token** (`create_access_token`): payload `sub` = `str(user_id)`, `type: "access"`, `exp` = teraz + `ACCESS_TOKEN_EXPIRE_MINUTES` (domyślnie 15).
- **Refresh token** (`create_refresh_token`): `sub`, unikalne **`jti`** (UUID), `type: "refresh"`, `exp` = teraz + `REFRESH_TOKEN_EXPIRE_DAYS` (domyślnie 7). Para `(token_string, jti)` - `jti` zapisuje się w DB jako `RefreshToken.id`.

**Dekodowanie:** `decode_access_token` / `decode_refresh_token` - przy błędzie podpisu lub typu rzucany jest `ValueError`.

### Logowanie i tokeny (`controllers/auth_controller.py`, `services/auth_service.py`)

1. **`POST /auth/login`** (body: email + hasło) - `AuthService.authenticate`; przy sukcesie `issue_tokens`: access JWT + refresh JWT, zapis `RefreshToken` w DB; refresh dodatkowo w **cookie** `HttpOnly` `refresh_token` (ścieżka `/auth`, `SameSite=lax`, opcjonalnie `Secure` przez `REFRESH_COOKIE_SECURE`).
2. Odpowiedź JSON zawiera też `access_token` i `refresh_token` (frontend może trzymać refresh w pamięci lub polegać na cookie).
3. **`POST /auth/refresh`** - refresh z cookie **lub** z JSON `{ "refresh_token": "..." }`; `rotate_tokens`: walidacja `jti`, sprawdzenie `revoked` i `expires_at`, **unieważnienie starego** rekordu, wystawienie **nowej pary** (rotacja). Przy podejrzeniu reuse (token już unieważniony) - `revoke_all_for_user` w repozytorium (sygnał kompromitacji).
4. **`POST /auth/logout`** - odczyt refresh, `revoke_token`, usunięcie cookie.

### Chronione endpointy REST (`app.py`)

Routery `server_router`, `channel_router`, `message_router` mają globalną zależność:

```python
dependencies=[Depends(get_current_user)]
```

`get_current_user` (`core/dependencies.py`):

- Pobiera nagłówek **`Authorization: Bearer <access_token>`** (schemat OAuth2 z `tokenUrl="/auth/login"` - to URL symboliczny; faktyczne logowanie to JSON `UserLogin`).
- Dekoduje access JWT → `user_id`, ładuje `User` z bazy; brak usera lub zły token → **401**.

### RBAC na serwerze (`core/dependencies.py`)

- `require_server_role(MemberRole.XXX)` - fabryka zależności: na podstawie `server_id` z ścieżki sprawdza `ServerMember` dla `current_user.id`.
- Hierarchia: `MEMBER` < `MODERATOR` < `ADMIN` < `OWNER`.
- Aliasy: `AnyServerMember`, `ServerModerator`, `ServerAdmin`, `ServerOwner` - używane w kontrolerach serwera/kanałów.

### WebSocket (`ws/channel_ws.py`)

- **Nie** przechodzi przez `OAuth2PasswordBearer`.
- Uwierzytelnianie: query **`?token=<access_jwt>`** - `decode_access_token`; walidacja usera i kanału przed `accept`.

---

## Czat: wiadomości, REST i realtime

### REST - wiadomości (`controllers/message_controller.py`)

| Metoda | Ścieżka | Opis |
|--------|---------|------|
| `POST` | `/channels/{channel_id}/messages` | Nowa wiadomość tekstowa (`MessageCreate`). Po zapisie: `message_to_response` + broadcast do **socketów tekstowych** (`manager.broadcast`) **oraz** do **wszystkich socketów głosowych** na tym kanale (`manager.broadcast_voice_all`) - ten sam payload co realtime, żeby klienci na VOICE dostali czat bez drugiego połączenia typu „tylko czat”. |
| `POST` | `/channels/{channel_id}/messages/image` | Multipart: plik + `caption`. Tylko **`ChannelType.TEXT`**; zapis skompresowanego WebP do MinIO, `image_key` na wiadomości. |
| `GET` | `/channels/{channel_id}/messages` | Paginacja `limit` / `offset` (auth przez globalny dependency na routerze - w kodzie kontrolera nie ma `CurrentUser`, ale router jest pod `_auth`). |
| `PATCH` | `/messages/{message_id}` | Edycja własnej wiadomości. |
| `DELETE` | `/messages/{message_id}` | Usunięcie własnej wiadomości. |

### Odpowiedź wiadomości (`schemas/message.py`)

`MessageResponse` zawiera m.in. `author_username`, `author_avatar_url` (presigned jeśli `avatar_url` w DB to klucz S3), `image_url` (**presigned GET** z `image_key`, nie publiczny URL bucketu).

### WebSocket kanału (`ws/channel_ws.py`)

Jeden endpoint: **`/ws/channels/{channel_id}?token=...`**.

**Kanał `TEXT`:**

- Połączenie: `manager.connect` (zbiór socketów „czat tekstowy”).
- Pętla: JSON z polem `content` (1–4000 znaków) → zapis wiadomości → `broadcast` tego samego payloadu co `message_realtime_payload` do wszystkich podłączonych do kanału.

**Kanał `VOICE`:**

- Połączenie: `manager.connect_voice` (osobna mapa socket → `user_id`).
- Start: do klienta `voice_room` / `peers`; do innych `peer_joined`.
- Pętla:
  - **`type: "voice_signal"`** - forward WebRTC (`offer` / `answer` / `ice`) do wskazanego `to` (UUID usera).
  - **Pole `content`** (bez `voice_signal`) - zapis wiadomości jak REST + **`broadcast_voice_all`** (czat z poziomu WS na kanale głosowym).
- Rozłączenie: `peer_left` do pozostałych.

**`ws/connection_manager.py`:** dwa „pokoje” na `channel_id`: `_channels` (TEXT) i `_voice` (VOICE); metody `broadcast`, `broadcast_voice_all`, `send_voice_to_user`, itd.

### MinIO / S3 (`core/media_s3.py`, `config/envs.py`)

- Obrazy czatu i avatary w bucketcie; **`signed_image_url`** dla odczytu w przeglądarce bez Bearer.
- Zmienne: `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_PUBLIC_URL`, opcjonalnie `MINIO_DISABLED=1` (upload zwraca 503).

### Lista uczestników voice (`controllers/channel_controller.py`)

- **`GET /channels/{channel_id}/voice/participants`** - wymaga członkostwa na serwerze kanału; zwraca `{ user_id, username }[]` z aktualnych socketów głosowych + hydratacja nazw z `UserRepository`.

---

## Pozostałe endpointy (skrót)

- **`user_controller`:** rejestracja (`/users/register` - publiczny), profil (`/users/me`), avatar (`POST/DELETE /users/me/avatar`), itd.
- **`server_controller`:** listowanie serwerów użytkownika, tworzenie, zaproszenia, członkowie.
- **`channel_controller`:** kanały per serwer, CRUD z rolami, `GET /channels/{id}`, voice participants jak wyżej.

---

## Testy i migracje

- **`pytest`** w katalogu `tests/`.
- **`core/startup_db.py`** - migracje startowe (np. kolumny w `messages`), wywoływane w `lifespan` w `app.py`.

---

## Podsumowanie przepływu „czat”

1. Użytkownik loguje się → access JWT + refresh (DB + opcjonalnie cookie).
2. Żądania REST (serwery, kanały, wiadomości) z nagłówkiem **Bearer access**.
3. **TEXT:** opcjonalnie WebSocket do wysyłki/odbioru live; **VOICE:** jeden WebSocket na sygnalizację + ten sam strumień payloadów co wiadomości.
4. Obrazy: upload → MinIO → w DB `image_key`; klient dostaje **presigned** `image_url` w JSON.

Jeśli rozszerzasz API, trzymaj spójność: **modele** = źródło prawdy o tabelach, **schemas** = kontrakt HTTP, **services** = reguły biznesowe.
