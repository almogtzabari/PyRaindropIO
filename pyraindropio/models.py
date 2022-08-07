from typing import Iterator, List, Dict
import requests
import math
from .constants import BASE_API_URL, MAX_ITEMS_PER_PAGE
import concurrent.futures
import threading
import time


LOCK = threading.Lock()


def _get_headers(access_token: str):
    return {"Authorization": f"Bearer {access_token}"}


def fetch_response(request, url, headers, params={}):
    while True:
        response = request(
                url=url,
                headers=headers,
                params=params
        )
        if all([
            'retry-after' not in response.headers,
            response.status_code == 200
        ]):
            return response
        
        wait = response.headers.get('retry-after')
        if wait is None:
            wait = 10
            msg = f'PyRaindropIO - bad response recieved from Raindrop.io API. Retrying in 10 seconds...'
        else:
            msg = f'PyRaindropIO - waiting {int(wait)} seconds for Raindrop.io API to allow more requests.'
        with LOCK:
            print(msg)

        time.sleep(int(wait)+1)


class Session:
    def __init__(self, access_token: str, max_threads: int=4) -> None:
        self._access_token = access_token
        self._max_threads = max_threads
        self._collections: Dict['Collection'] = {}
        
    def get_collection_by_id(self, collection_id: int) -> 'Collection':
        if collection_id not in self._collections:
            response = fetch_response(
                request=requests.get,
                url=f"{BASE_API_URL}/collection/{collection_id}",
                headers=_get_headers(self._access_token)
            )
            data = response.json()
            collection_dict = data['item']
            collection = Collection(collection_dict, access_token=self._access_token, max_threads=self._max_threads)
            self._collections[collection_id] = collection

        return self._collections[collection_id]


class Collection:
    id: int
    access: dict
    color: str
    count: int
    cover: List[str]
    created: str
    expanded: bool
    last_update: str
    parent: dict
    public: bool
    sort: int
    title: str
    user: dict
    view: str
    collaborators: bool
    raindrops: Dict[str, 'Raindrop']

    def __init__(self, collection_dict: dict, access_token: str, max_threads: int) -> None:
        self._dict = None
        self._access_token = access_token
        self._max_threads = max_threads
        self._raindrops = {}
        self.update_dict(collection_dict)

    def update_dict(self, new_collection_dict: dict) -> None:
        self._dict = new_collection_dict

    @property
    def id(self) -> int:
        return self._dict['_id']
    
    @property
    def access(self) -> dict:
        return self._dict['access']

    @property
    def color(self) -> str:
        return self._dict['color']

    @property
    def count(self) -> int:
        return self._dict['count']

    @property
    def cover(self) -> List[str]:
        return self._dict['cover']

    @property
    def created(self) -> str:
        return self._dict['created']

    @property
    def expanded(self) -> bool:
        return self._dict['expanded']

    @property
    def last_update(self) -> str:
        return self._dict['lastUpdate']

    @property
    def parent(self) -> dict:
        return self._dict['parent']

    @property
    def public(self) -> bool:
        return self._dict['public']

    @property
    def sort(self) -> int:
        return self._dict['sort']

    @property
    def title(self) -> str:
        return self._dict['title']

    @property
    def user(self) -> dict:
        return self._dict['user']

    @property
    def view(self) -> str:
        return self._dict['view']

    @property
    def collaborators(self) -> bool:
        return self._dict.get('collaborators', False)

    @property
    def raindrops(self) -> int:
        return self._raindrops

    def __iter__(self) -> Iterator['Raindrop']:
        return iter(self._raindrops.values())
    
    def __getitem__(self, raindrop_id: int) -> 'Raindrop':
        return self._raindrops.get(raindrop_id)

    def fetch_all_raindrops(self):
        return self.search(search_str=None)

    def search(self, search_str: str=None) -> Iterator['Raindrop']:
        def create_or_update_raindrop_from_raindrop_dict(raindrop_dict):
            with LOCK:
                raindrop = self._raindrops.get(raindrop_dict['_id'])

            if raindrop is None:
                raindrop = Raindrop(raindrop_dict, access_token=self._access_token)
            else:
                raindrop.update_dict(raindrop_dict)

            return raindrop
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_threads) as executor:
            futures = []
            for page in range(0, math.ceil(self.count / MAX_ITEMS_PER_PAGE)):
                response = fetch_response(
                    request=requests.get,
                    url=f"{BASE_API_URL}/raindrops/{self.id}",
                    params={
                        'search': search_str,
                        'page': page,
                        'perpage': MAX_ITEMS_PER_PAGE
                    },
                    headers=_get_headers(self._access_token)
                )
                for raindrop_dict in response.json()['items']:
                    futures.append(
                        executor.submit(
                            create_or_update_raindrop_from_raindrop_dict,
                            raindrop_dict=raindrop_dict,
                        )
                    )

            for future in concurrent.futures.as_completed(futures):
                raindrop = future.result()
                with LOCK:
                    self._raindrops[raindrop.id] = raindrop
                yield raindrop


class Raindrop:
    id: int
    collection: dict
    cover: str
    created: str
    domain: str
    excerpt: str
    last_update: str
    link: str
    media: List[dict]
    tags: List[str]
    title: str
    type: str
    user: dict
    highlights: List['Highlight']

    def __init__(self, raindrop_dict: dict, access_token: str) -> None:
        self._dict = None
        self._access_token = access_token
        self._highlights = []
        self.update_dict(raindrop_dict)

    def update_dict(self, new_raindrop_dict: dict) -> None:
        self._dict = new_raindrop_dict
        self.fetch_highlights()

    @property
    def id(self) -> int:
        return self._dict['_id']

    @property
    def collection(self) -> str:
        return self._dict['collection']
    
    @property
    def cover(self) -> str:
        return self._dict['cover']

    @property
    def created(self) -> str:
        return self._dict['created']

    @property
    def domain(self) -> str:
        return self._dict['domain']

    @property
    def last_update(self) -> str:
        return self._dict['lastUpdate']

    @property
    def link(self) -> str:
        return self._dict['link']

    @property
    def media(self) -> List[dict]:
        return self._dict['media']

    @property
    def tags(self) -> List[str]:
        return self._dict['tags']

    @property
    def title(self) -> str:
        return self._dict['title']

    @property
    def type(self) -> str:
        return self._dict['type']

    @property
    def user(self) -> dict:
        return self._dict['user']

    @property
    def highlights(self) -> List['Highlight']:
        return self._highlights

    def __iter__(self) -> Iterator['Highlight']:
        return iter(self._highlights)

    def fetch_highlights(self):
        self._highlights = []
        response = fetch_response(
            request=requests.get,
            url=f"{BASE_API_URL}/raindrop/{self.id}",
            headers=_get_headers(self._access_token)
        )
        data = response.json()

        for highlight_dict in data['item']['highlights']:
            highlight = Highlight(highlight_dict=highlight_dict)
            self._highlights.append(highlight)

        return self

        
class Highlight:
    id: int
    text: str
    color: str
    note: str
    created: str

    def __init__(self, highlight_dict: dict) -> None:
        self._highlight_dict = highlight_dict

    def update_dict(self, new_highlight_dict: dict) -> None:
        self._highlight_dict = new_highlight_dict

    @property
    def id(self) -> int:
        return self._highlight_dict['_id']

    @property
    def text(self) -> int:
        return self._highlight_dict['text']

    @property
    def color(self) -> int:
        return self._highlight_dict.get('color', 'yellow')  # BUG? Why is this missing for some highlights?

    @property
    def note(self) -> int:
        return self._highlight_dict['note']

    @property
    def created(self) -> int:
        return self._highlight_dict['created']

    def __repr__(self) -> str:
        return f"Highlight(id={self.id}, created={self.created})"

    def __str__(self) -> str:
        return str({
            'id': self.id,
            'text': self.text,
            'color': self.color,
            'note': self.note,
            'created': self.created
        })