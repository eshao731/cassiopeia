from typing import List, Union, Optional, Generator

from merakicommons.cache import lazy_property, lazy
from merakicommons.container import searchable, SearchableList

from .. import configuration
from ..data import Region, Platform, Tier, Division, Queue, Role, Position
from .common import CoreData, CoreDataList, CassiopeiaObject, CassiopeiaGhost, CassiopeiaLazyList, provide_default_region, ghost_load_on
from ..dto.league import LeaguePositionDto, LeaguePositionsDto,  LeaguesListDto, LeagueListDto, MiniSeriesDto, GrandmasterLeagueListDto, ChallengerLeagueListDto, MasterLeagueListDto, PositionalLeaguesListDto, PositionalQueuesDto
from .summoner import Summoner


##############
# Data Types #
##############


class PositionalQueuesData(CoreDataList):
    _dto_type = PositionalQueuesDto
    _renamed = {}


class MiniSeriesData(CoreData):
    _dto_type = MiniSeriesDto
    _renamed = {}


class LeaguePositionData(CoreData):
    _dto_type = LeaguePositionDto
    _renamed = {"miniSeries": "promos", "playerOrTeamId": "summonerId", "playerOrTeamName": "summonerName", "leagueName": "name", "queueType": "queue", "rank": "division"}

    def __call__(self, **kwargs):
        if "miniSeries" in kwargs:
            self.promos = MiniSeriesData(**kwargs.pop("miniSeries"))
        if "summonerId" in kwargs:
            self.summonerId = kwargs.pop("summonerId")
        super().__call__(**kwargs)
        return self


class LeaguePositionsData(CoreDataList):
    _dto_type = LeaguePositionsDto
    _renamed = {}


class LeagueListData(CoreData):
    _dto_type = LeagueListDto
    _renamed = {"leagueId": "id"}

    def __call__(self, **kwargs):
        if "entries" in kwargs:
            self.entries = [LeaguePositionData(**entry) for entry in kwargs.pop("entries")]
        super().__call__(**kwargs)
        return self


class LeaguesListData(CoreDataList):
    _dto_type = LeaguesListDto
    _renamed = {}


class PositionalLeaguesListData(CoreDataList):
    _dto_type = PositionalLeaguesListDto
    _renamed = {}


class ChallengerLeagueListData(CoreData):
    _dto_type = ChallengerLeagueListDto
    _renamed = {"leagueId": "id"}

    def __call__(self, **kwargs):
        if "entries" in kwargs:
            self.entries = [LeaguePositionData(**entry) for entry in kwargs.pop("entries")]
        super().__call__(**kwargs)
        return self

class GrandmasterLeagueListData(CoreData):
    _dto_type = GrandmasterLeagueListDto
    _renamed = {"leagueId": "id"}

    def __call__(self, **kwargs):
        if "entries" in kwargs:
            self.entries = [LeaguePositionData(**entry) for entry in kwargs.pop("entries")]
        super().__call__(**kwargs)
        return self

class MasterLeagueListData(CoreData):
    _dto_type = MasterLeagueListDto
    _renamed = {"leagueId": "id"}

    def __call__(self, **kwargs):
        if "entries" in kwargs:
            self.entries = [LeaguePositionData(**entry) for entry in kwargs.pop("entries")]
        super().__call__(**kwargs)
        return self


##############
# Core Types #
##############


class PositionalQueues(CassiopeiaLazyList):
    _data_types = {PositionalQueuesData}

    @provide_default_region
    def __init__(self, *, region: Union[Region, str] = None):
        kwargs = {"region": region}
        CassiopeiaObject.__init__(self, **kwargs)


class MiniSeries(CassiopeiaObject):
    _data_types = {MiniSeriesData}
    # Technically wins, loses, and wins_required can all be calculated from progress, so we don't technically need to store those data.

    def __str__(self):
        return f"Promos{self.progress + [None for _ in range(self.not_played)]}"

    @property
    def wins(self) -> int:
        return self._data[MiniSeriesData].wins  # sum(self.progress)  # This will work too

    @property
    def losses(self) -> int:
        return self._data[MiniSeriesData].losses  # len(self._data[MiniSeriesData].progress[0]) - sum(self.progress)  # This will work too

    @property
    def wins_required(self) -> int:
        """2 or 3 wins will be required for promotion."""
        return self._data[MiniSeriesData].target  # {3: 2, 5: 3}[len(self._data[MiniSeriesData].progress[0])]

    @property
    def not_played(self) -> int:
        """The number of games in the player's promos that they haven't played yet."""
        return len(self._data[MiniSeriesData].progress) - len(self.progress)

    @lazy_property
    def progress(self) -> List[bool]:
        """A list of True/False for the number of games the played in the mini series indicating if the player won or lost."""
        return [True if p == "W" else False for p in self._data[MiniSeriesData].progress if p != "N"]


@searchable({str: ["division", "name", "summoner"], bool: ["hot_streak", "veteran", "fresh_blood"], Division: ["division"], Summoner: ["summoner"], Queue: ["queue"]})
class LeagueEntry(CassiopeiaGhost):
    _data_types = {LeaguePositionData}

    @provide_default_region
    def __init__(self, *, region: Union[Region, str] = None):
        kwargs = {"region": region}
        super().__init__(**kwargs)

    def __get_query__(self):
        return {"region": self.region, "platform": self.platform}

    def __eq__(self, other: "LeagueEntry"):
        if not isinstance(other, LeagueEntry) or self.region != other.region:
            return False
        return self.summoner == other.summoner and self.queue == other.queue and self.name == other.name

    __hash__ = CassiopeiaGhost.__hash__

    @lazy_property
    def region(self) -> Region:
        """The region for this champion."""
        return Region(self._data[LeaguePositionData].region)

    @lazy_property
    def platform(self) -> Platform:
        """The platform for this champion."""
        return self.region.platform

    @property
    def league_id(self) -> str:
        return self._data[LeaguePositionData].leagueId

    @lazy_property
    def queue(self) -> Queue:
        return Queue(self._data[LeaguePositionData].queue)

    @property
    def name(self) -> str:
        return self._data[LeaguePositionData].name

    @lazy_property
    def tier(self) -> Tier:
        return Tier(self._data[LeaguePositionData].tier)

    @lazy_property
    def position(self) -> Position:
        return Position(self._data[LeaguePositionData].position)

    @lazy_property
    def division(self) -> Division:
        return Division(self._data[LeaguePositionData].division)

    @property
    def hot_streak(self) -> bool:
        return self._data[LeaguePositionData].hotStreak

    @lazy_property
    def promos(self) -> Optional[MiniSeries]:
        if hasattr(self._data[LeaguePositionData], "promos"):
            return MiniSeries.from_data(self._data[LeaguePositionData].promos)
        else:
            # Return None if the summoner isn't in their promos
            if hasattr(self._data[LeaguePositionData], "leaguePoints"):
                return None
        # Reraise the original error
        return MiniSeries.from_data(self._data[LeaguePositionData].promos)

    @property
    def wins(self) -> int:
        return self._data[LeaguePositionData].wins

    @property
    def veteran(self) -> bool:
        return self._data[LeaguePositionData].veteran

    @property
    def losses(self) -> int:
        return self._data[LeaguePositionData].losses

    @lazy_property
    def summoner(self) -> Summoner:
        return Summoner(id=self._data[LeaguePositionData].summonerId, name=self._data[LeaguePositionData].summonerName, region=self.region)

    @property
    def fresh_blood(self) -> bool:
        return self._data[LeaguePositionData].freshBlood

    @lazy_property
    def league(self) -> "League":
        return League(id=self.league_id, region=self.region)

    @property
    def league_points(self) -> int:
        return self._data[LeaguePositionData].leaguePoints

    @property
    def inactive(self) -> bool:
        return self._data[LeaguePositionData].inactive

    @property
    def role(self) -> Role:
        return Role.from_league_naming_scheme(self._data[LeaguePositionData].role)


class LeagueEntries(CassiopeiaLazyList):
    _data_types = {LeaguePositionsData}

    @provide_default_region
    def __init__(self, *, summoner: Summoner, region: Union[Region, str] = None):
        self.__summoner = summoner
        kwargs = {"region": region}
        CassiopeiaObject.__init__(self, **kwargs)

    @classmethod
    @provide_default_region
    def __get_query_from_kwargs__(cls, *, summoner: Union[Summoner, str], region: Union[Region, str]) -> dict:
        query = {"region": region}
        if isinstance(summoner, Summoner):
            query["summoner.id"] = summoner.id
        elif isinstance(summoner, str):
            if len(summoner) < 35:
                query["summoner.id"] = Summoner(name=summoner, region=region).id
            else:
                query["summoner.id"] = summoner
        assert "summoner.id" in query
        return query

    @lazy_property
    def region(self) -> Region:
        return Region(self._data[LeaguePositionsData].region)

    @lazy_property
    def platform(self) -> Platform:
        return self.region.platform

    @property
    def fives(self):
        return self[Queue.ranked_solo_fives]

    @property
    def flex(self):
        return self[Queue.ranked_flex_fives]

    @property
    def threes(self):
        return self[Queue.ranked_flex_threes]


class PositionalLeagues(CassiopeiaLazyList):  # type List[LeagueEntry]
    _data_types = {PositionalLeaguesListData}

    @provide_default_region
    def __init__(self, *, region: Union[Region, str] = None, queue: Queue = None, tier: Tier = None, division: Division = None, position: Position = None):
        kwargs = {"region": region, "queue": queue, "tier": tier, "division": division, "position": position}
        CassiopeiaObject.__init__(self, **kwargs)

    @classmethod
    @provide_default_region
    def __get_query_from_kwargs__(cls, *, region: Union[Region, str] = None, queue: Queue = None, tier: Tier = None, division: Division = None, position: Position = None):
        query = {"region": region, "queue": queue, "tier": tier, "division": division, "position": position}
        return query

    @classmethod
    def from_generator(cls, generator: Generator, region: Union[Region, str] = None, queue: Queue = None, tier: Tier = None, division: Division = None, position: Position = None, **kwargs):
        self = cls.__new__(cls)
        kwargs["region"] = region
        kwargs["queue"] = queue
        kwargs["tier"] = tier
        kwargs["division"] = division
        kwargs["position"] = position
        CassiopeiaLazyList.__init__(self, generator=generator, **kwargs)
        return self

    @lazy_property
    def region(self) -> Region:
        return Region(self._data[PositionalLeaguesListData].region)

    @lazy_property
    def platform(self) -> Platform:
        return self.region.platform

    @lazy_property
    def queue(self) -> Queue:
        return Queue(self._data[PositionalLeaguesListData].queue)

    @lazy_property
    def tier(self) -> Tier:
        return Tier(self._data[PositionalLeaguesListData].tier)

    @lazy_property
    def division(self) -> Division:
        return Division(self._data[PositionalLeaguesListData].division)

    @lazy_property
    def position(self) -> Position:
        return Position(self._data[PositionalLeaguesListData].position)



class SummonerLeagues(dict):
    """A helper class that is simply a searchable list but that also provides the below convenience methods."""
    @property
    def fives(self):
        return self[Queue.ranked_solo_fives]

    @property
    def flex(self):
        return self[Queue.ranked_flex_fives]

    @property
    def threes(self):
        return self[Queue.ranked_flex_threes]


@searchable({str: ["tier", "queue", "name"], Queue: ["queue"], Tier: ["tier"]})
class League(CassiopeiaGhost):
    _data_types = {LeagueListData}

    def __init__(self, id: str = None, region: Union[Region, str] = None):
        if region is None:
            region = configuration.settings.default_region
        if region is not None and not isinstance(region, Region):
            region = Region(region)
        kwargs = {"id": id, "region": region}
        super().__init__(**kwargs)

    def __get_query__(self):
        return {"id": self.id, "region": self.region, "platform": self.platform}

    def __eq__(self, other: "League"):
        if not isinstance(other, League) or self.region != other.region:
            return False
        return self.id == other.id

    def __str__(self):
        region = self.region
        id_ = self.id
        return "League(id={id_}, region='{region}')".format(id_=id_, region=region.value)

    __hash__ = CassiopeiaGhost.__hash__

    def __getitem__(self, item):
        return self.entries[item]

    def __len__(self):
        return len(self.entries)

    @lazy_property
    def region(self) -> Region:
        return Region(self._data[LeagueListData].region)

    @lazy_property
    def platform(self) -> Platform:
        return self.region.platform

    @property
    def id(self) -> str:
        return self._data[LeagueListData].id

    @CassiopeiaGhost.property(LeagueListData)
    @ghost_load_on
    @lazy
    def tier(self) -> Tier:
        return Tier(self._data[LeagueListData].tier)

    @CassiopeiaGhost.property(LeagueListData)
    @ghost_load_on
    @lazy
    def queue(self) -> Queue:
        return Queue(self._data[LeagueListData].queue)

    @CassiopeiaGhost.property(LeagueListData)
    @ghost_load_on
    def name(self) -> str:
        return self._data[LeagueListData].name

    @CassiopeiaGhost.property(LeagueListData)
    @ghost_load_on
    @lazy
    def entries(self) -> List[LeagueEntry]:
        return SearchableList([LeagueEntry.from_data(entry) for entry in self._data[LeagueListData].entries])


class ChallengerLeague(CassiopeiaGhost):
    _data_types = {ChallengerLeagueListData}

    @provide_default_region
    def __init__(self, *, queue: Union[Queue, str, int] = None, region: Union[Region, str] = None):
        kwargs = {"region": region}
        if isinstance(queue, int):
            kwargs["queue"] = Queue.from_id(queue)
        elif isinstance(queue, str):
            kwargs["queue"] = Queue(queue)
        elif isinstance(queue, Queue):
            kwargs["queue"] = queue
        super().__init__(**kwargs)

    def __get_query__(self):
        return {"region": self.region, "platform": self.platform, "queue": self.queue}

    def __getitem__(self, item):
        return self.entries[item]

    def __len__(self):
        return len(self.entries)

    def __eq__(self, other: "ChallengerLeague"):
        if not isinstance(other, ChallengerLeague) or self.region != other.region:
            return False
        return self.queue == other.queue

    __hash__ = CassiopeiaGhost.__hash__

    @lazy_property
    def region(self) -> Region:
        return Region(self._data[ChallengerLeagueListData].region)

    @lazy_property
    def platform(self) -> Platform:
        return self.region.platform
    
    @CassiopeiaGhost.property(ChallengerLeagueListData)
    @ghost_load_on
    def id(self) -> str:
        return self._data[ChallengerLeagueListData].id

    @lazy_property
    def tier(self) -> Tier:
        return Tier.challenger

    @lazy_property
    def queue(self) -> Queue:
        return Queue(self._data[ChallengerLeagueListData].queue)

    @CassiopeiaGhost.property(ChallengerLeagueListData)
    @ghost_load_on
    def name(self) -> str:
        return self._data[ChallengerLeagueListData].name

    @CassiopeiaGhost.property(ChallengerLeagueListData)
    @ghost_load_on
    @lazy
    def entries(self) -> List[LeagueEntry]:
        return SearchableList([LeagueEntry.from_data(entry) for entry in self._data[ChallengerLeagueListData].entries])

class GrandmasterLeague(CassiopeiaGhost):
    _data_types = {GrandmasterLeagueListData}

    @provide_default_region
    def __init__(self, *, queue: Union[Queue, str, int] = None, region: Union[Region, str] = None):
        kwargs = {"region": region}
        if isinstance(queue, int):
            kwargs["queue"] = Queue.from_id(queue)
        elif isinstance(queue, str):
            kwargs["queue"] = Queue(queue)
        elif isinstance(queue, Queue):
            kwargs["queue"] = queue
        super().__init__(**kwargs)

    def __get_query__(self):
        return {"region": self.region, "platform": self.platform, "queue": self.queue}

    def __eq__(self, other: "GrandmasterLeague"):
        if not isinstance(other, GrandmasterLeague) or self.region != other.region:
            return False
        return self.queue == other.queue

    __hash__ = CassiopeiaGhost.__hash__

    def __getitem__(self, item):
        return self.entries[item]

    def __len__(self):
        return len(self.entries)

    @lazy_property
    def region(self) -> Region:
        return Region(self._data[GrandmasterLeagueListData].region)

    @lazy_property
    def platform(self) -> Platform:
        return self.region.platform

    @CassiopeiaGhost.property(GrandmasterLeagueListData)
    @ghost_load_on
    def id(self) -> str:
        return self._data[GrandmasterLeagueListData].id

    @lazy_property
    def tier(self) -> Tier:
        return Tier.grandmaster

    @lazy_property
    def queue(self) -> Queue:
        return Queue(self._data[GrandmasterLeagueListData].queue)

    @CassiopeiaGhost.property(GrandmasterLeagueListData)
    @ghost_load_on
    def name(self) -> str:
        return self._data[GrandmasterLeagueListData].name

    @CassiopeiaGhost.property(GrandmasterLeagueListData)
    @ghost_load_on
    @lazy
    def entries(self) -> List[LeagueEntry]:
        return SearchableList([LeagueEntry.from_data(entry) for entry in self._data[GrandmasterLeagueListData].entries])

class MasterLeague(CassiopeiaGhost):
    _data_types = {MasterLeagueListData}

    @provide_default_region
    def __init__(self, *, queue: Union[Queue, str, int] = None, region: Union[Region, str] = None):
        kwargs = {"region": region}
        if isinstance(queue, int):
            kwargs["queue"] = Queue.from_id(queue)
        elif isinstance(queue, str):
            kwargs["queue"] = Queue(queue)
        elif isinstance(queue, Queue):
            kwargs["queue"] = queue
        super().__init__(**kwargs)

    def __get_query__(self):
        return {"region": self.region, "platform": self.platform, "queue": self.queue}

    def __eq__(self, other: "MasterLeague"):
        if not isinstance(other, MasterLeague) or self.region != other.region:
            return False
        return self.queue == other.queue

    __hash__ = CassiopeiaGhost.__hash__

    def __getitem__(self, item):
        return self.entries[item]

    def __len__(self):
        return len(self.entries)

    @lazy_property
    def region(self) -> Region:
        return Region(self._data[MasterLeagueListData].region)

    @lazy_property
    def platform(self) -> Platform:
        return self.region.platform

    @CassiopeiaGhost.property(MasterLeagueListData)
    @ghost_load_on
    def id(self) -> str:
        return self._data[MasterLeagueListData].id

    @lazy_property
    def tier(self) -> Tier:
        return Tier.master

    @lazy_property
    def queue(self) -> Queue:
        return Queue(self._data[MasterLeagueListData].queue)

    @CassiopeiaGhost.property(MasterLeagueListData)
    @ghost_load_on
    def name(self) -> str:
        return self._data[MasterLeagueListData].name

    @CassiopeiaGhost.property(MasterLeagueListData)
    @ghost_load_on
    @lazy
    def entries(self) -> List[LeagueEntry]:
        return SearchableList([LeagueEntry.from_data(entry) for entry in self._data[MasterLeagueListData].entries])