from typing import Iterator, List, Dict
from dataclasses import dataclass, field
import requests
import math
from pyraindropio.constants import BASE_API_URL, MAX_ITEMS_PER_PAGE
import concurrent.futures


def _get_headers(access_token: str):
    return {"Authorization": f"Bearer {access_token}"}


class Session:
    def __init__(self, access_token: str, max_threads: int=4) -> None:
        self._access_token = access_token
        self._max_threads = max_threads
        self._collections: Dict['Collection'] = {}
        
    def get_collection_by_id(self, collection_id: int) -> 'Collection':
        if collection_id not in self._collections:
            response = requests.get(url=f"{BASE_API_URL}/collection/{collection_id}", headers=_get_headers(self._access_token))
            data = response.json()
            collection_dict = data['item']
            collection = Collection(
                id=collection_dict['_id'],
                access=collection_dict['access'],
                color=collection_dict['color'],
                count=collection_dict['count'],
                cover=collection_dict['cover'],
                created=collection_dict['created'],
                expanded=collection_dict['expanded'],
                last_update=collection_dict['lastUpdate'],
                parent=collection_dict.get('parent'),
                public=collection_dict['public'],
                sort=collection_dict['sort'],
                title=collection_dict['title'],
                user=collection_dict['user'],
                view=collection_dict['view'],
                collaborators=collection_dict.get('collaborators'),
                _session=self
            )
            self._collections[collection_id] = collection

        return self._collections[collection_id]


@dataclass
class Collection:
    """
    See [documentation](https://developer.raindrop.io/v1/collections).
    """
    id: int
    access: dict
    color: str
    count: int
    cover: list[str]
    created: str
    expanded: bool
    last_update: str
    parent: 'Collection'
    public: bool
    sort: int
    title: str
    user: dict
    view: str
    _session: 'Session'
    collaborators: bool = field(default=False)
    _raindrops: Dict[str, 'Raindrop'] = field(default_factory=dict)

    def __iter__(self) -> Iterator['Raindrop']:
        self.search(search_str=None)  # All raindrops
        return iter(self._raindrops.values())
    
    def __getitem__(self, raindrop_id: int) -> 'Raindrop':
        raise NotImplementedError

    def search(self, search_str: str=None) -> Iterator['Raindrop']:
        def fetch_response(page: int, search: str):
            return requests.get(
                url=f"{BASE_API_URL}/raindrops/{self.id}",
                params={'search': search, 'page': page, 'perpage': MAX_ITEMS_PER_PAGE},
                headers=_get_headers(self._session._access_token),
            )

        results: List['Raindrop'] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self._session._max_threads) as executor:
            futures = []
            for page in range(0, math.ceil(self.count / MAX_ITEMS_PER_PAGE)):
                futures.append(executor.submit(fetch_response, page=page, search=search_str))
            for future in concurrent.futures.as_completed(futures):
                response = future.result()
                data = response.json()
                for raindrop_dict in data['items']:
                    if raindrop_dict['_id'] not in self._raindrops:
                        raindrop = Raindrop(
                            id=raindrop_dict['_id'],
                            collection=raindrop_dict['collection'],
                            cover=raindrop_dict['cover'],
                            created=raindrop_dict['created'],
                            domain=raindrop_dict['domain'],
                            excerpt=raindrop_dict['excerpt'],
                            last_update=raindrop_dict['lastUpdate'],
                            link=raindrop_dict['link'],
                            media=raindrop_dict['media'],
                            tags=raindrop_dict['tags'],
                            title=raindrop_dict['title'],
                            type=raindrop_dict['type'],
                            user=raindrop_dict['user'],
                            _collection=self
                        )
                        self._raindrops[raindrop_dict['_id']] = raindrop
                    results.append(self._raindrops[raindrop_dict['_id']])
        
        return results



@dataclass
class Raindrop:
    id: int
    collection: str
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
    _collection: 'Collection'
    _highlights: List['Highlight'] = None

    def __post_init__(self):
        self.fetch_highlights()

    def __iter__(self) -> Iterator['Highlight']:
        return iter(self._highlights)

    def fetch_highlights(self):
        highlights = []
        response = requests.get(
                url=f"{BASE_API_URL}/raindrop/{self.id}",
                headers=_get_headers(self._collection._session._access_token),
        )
        data = response.json()
        for highlight_dict in data['item']['highlights']:
            highlight = Highlight(
                id=highlight_dict['_id'],
                text=highlight_dict['text'],
                color=highlight_dict['color'],
                note=highlight_dict['note'],
                created=highlight_dict['created'],
                tags=data['item']['tags'],
                link=data['item']['link'],
                _raindrop=self
            )
            highlights.append(highlight)
        
        self._highlights = highlights
        return self


@dataclass
class Highlight:
    id: int
    text: str
    color: str
    note: str
    created: str
    tags: list
    link: str

    # Non API
    _raindrop: 'Raindrop'