import io
import uuid
import time
import httpx
import secrets
from typing import Set
from typing import List
from typing import Literal
from typing import TypeVar
from typing import Sequence
from fastapi import Query
from fastapi import Request
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from fastapi.responses import PlainTextResponse
from fastapi.responses import RedirectResponse


# -- GLOBAL -- #
with open("eff_wordlist.txt", "r") as f:
    PASSPHRASE_WORD_LIST = [line.strip() for line in f if line.strip()]

app = FastAPI(
    title="MiscellaneousAPI",
    description="Random and somewhat useful endpoints!",
    version="1.0.0"
)
# -- END GLOBAL -- #


# -- HELPERS -- #
T = TypeVar("T")


def _secure_sample(items: Sequence[T], sample_size: int) -> List[T]:
    if sample_size > len(items):
        raise ValueError("Sample size cannot exceed the number of available items.")

    sampled_items: List[T] = []
    seen_indices: Set[int] = set()

    while len(sampled_items) < sample_size:
        index = secrets.randbelow(len(items))
        if index not in seen_indices:
            seen_indices.add(index)
            sampled_items.append(items[index])

    return sampled_items


def _secure_choice(items: Sequence[T]) -> T:
    index = secrets.randbelow(len(items))
    return items[index]


def _secure_randint(min_value: int, max_value: int) -> int:
    range_size = max_value - min_value + 1
    random_offset = secrets.randbelow(range_size)
    return min_value + random_offset
# -- END HELPERS -- #


@app.get("/", name="Redirect to /docs")
async def groot():
    return RedirectResponse(url="/docs", status_code=308)


@app.get("/teapot")
async def teapot():
    async with httpx.AsyncClient() as client:
        r = await client.get("https://http.cat/images/418.jpg")
        r.raise_for_status()
        content_type = r.headers.get("content-type") or "image/jpeg"
        return StreamingResponse(
            io.BytesIO(r.content),
            media_type=content_type,
            status_code=418,
        )


@app.get("/random-dog")
async def random_dog():
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get("https://dog.ceo/api/breeds/image/random")
            r.raise_for_status()

            url = r.json().get("message")
            breed = url.split("/")[4]

            if not url or not breed:
                raise Exception()

            return JSONResponse(
                content={"breed": breed, "url": url},
                media_type="application/json"
            )
        except Exception:
            return JSONResponse(
                content={"breed": None, "url": None},
                media_type="application/json",
                status_code=500,
            )


@app.get("/flip-coin")
async def flip_coin():
    result = _secure_randint(0, 1)
    return PlainTextResponse(content=str(result), media_type="text/plain")


@app.get("/roll-dice")
async def roll_dice(sides: int = Query(6, ge=2, le=1000)):
    result = _secure_randint(1, sides)
    return PlainTextResponse(content=str(result), media_type="text/plain")


@app.get("/random-number")
async def random_number(min: int = Query(1, ge=0), max: int = Query(100, le=1_000_000_000)):
    result = _secure_randint(min, max)
    return PlainTextResponse(content=str(result), media_type="text/plain")


@app.get("/random-string")
async def random_string(length: int = Query(10, ge=1, le=100)):
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    result = ''.join(_secure_choice(chars) for _ in range(length))
    return PlainTextResponse(content=result, media_type="text/plain")


@app.get("/random-uuid")
async def random_uuid(count: int = Query(1, ge=1, le=100)):
    results = [str(uuid.uuid4()) for _ in range(count)]
    return PlainTextResponse(content="\n".join(results), media_type="text/plain")


@app.get("/random-passphrase")
async def random_passphrase(
    words: int = Query(4, ge=1, le=20),
    numbers: bool = False,
    symbols: bool = False,
    separator: str = Query("-", min_length=0, max_length=3),
    case: Literal["lower", "upper", "title", "camel"] = "title"
):
    chosen_words = _secure_sample(PASSPHRASE_WORD_LIST, sample_size=words)

    if case == "lower":
        chosen_words = [word.lower() for word in chosen_words]
    elif case == "upper":
        chosen_words = [word.upper() for word in chosen_words]
    elif case == "title":
        chosen_words = [word.title() for word in chosen_words]
    elif case == "camel":
        chosen_words = [word.title() for word in chosen_words]
        chosen_words[0] = chosen_words[0].lower()
    else:
        pass  # just let it fail silently and default to title

    if numbers:
        index = _secure_randint(0, len(chosen_words) - 1)
        chosen_words[index] += str(_secure_randint(0, 9))

    if symbols:
        index = _secure_randint(0, len(chosen_words) - 1)
        random_symbols = "!@#$%&"

        if separator in random_symbols:
            random_symbols = random_symbols.replace(separator, "")

        chosen_words[index] += _secure_choice(random_symbols)

    result = separator.join(chosen_words)

    return PlainTextResponse(content=result, media_type="text/plain")


@app.get("/ip")
async def ip(request: Request):
    client_ip = request.client.host if request.client else None

    if client_ip in {"127.0.0.1", "0.0.0.0", "::1", "localhost", None}:
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return PlainTextResponse(content=cf_ip, media_type="text/plain")

        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            return PlainTextResponse(content=x_forwarded_for.split(",")[0].strip(), media_type="text/plain")

        return PlainTextResponse(content="", media_type="text/plain")

    return PlainTextResponse(content=client_ip, media_type="text/plain")


@app.get("/epoch-time")
async def epoch_time():
    return PlainTextResponse(content=str(int(time.time())), media_type="text/plain")


@app.get("/headers")
async def headers(request: Request):
    return JSONResponse(content=dict(request.headers))
