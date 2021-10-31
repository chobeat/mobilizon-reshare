from typing import Iterable, Optional, Dict
from uuid import UUID

from arrow import Arrow
from tortoise.queryset import QuerySet
from tortoise.transactions import atomic

from mobilizon_reshare.event.event import MobilizonEvent, EventPublicationStatus
from mobilizon_reshare.models.event import Event
from mobilizon_reshare.models.publication import Publication, PublicationStatus
from mobilizon_reshare.storage.query import CONNECTION_NAME


async def get_mobilizon_event_publications(
    event: MobilizonEvent,
) -> Iterable[Publication]:
    models = await prefetch_event_relations(
        Event.filter(mobilizon_id=event.mobilizon_id)
    )
    return models[0].publications


async def get_published_events(
    from_date: Optional[Arrow] = None, to_date: Optional[Arrow] = None
) -> Iterable[MobilizonEvent]:
    """
    Retrieves events that are not waiting. Function could be renamed to something more fitting
    :return:
    """
    return await events_with_status(
        [
            EventPublicationStatus.COMPLETED,
            EventPublicationStatus.PARTIAL,
            EventPublicationStatus.FAILED,
        ],
        from_date=from_date,
        to_date=to_date,
    )


async def events_with_status(
    status: list[EventPublicationStatus],
    from_date: Optional[Arrow] = None,
    to_date: Optional[Arrow] = None,
) -> Iterable[MobilizonEvent]:
    def _filter_event_with_status(event: Event) -> bool:
        # This computes the status client-side instead of running in the DB. It shouldn't pose a performance problem
        # in the short term, but should be moved to the query if possible.
        event_status = MobilizonEvent.compute_status(list(event.publications))
        return event_status in status

    query = Event.all()

    return map(
        MobilizonEvent.from_model,
        filter(
            _filter_event_with_status,
            await prefetch_event_relations(
                _add_date_window(query, "begin_datetime", from_date, to_date)
            ),
        ),
    )


async def get_all_events(
    from_date: Optional[Arrow] = None, to_date: Optional[Arrow] = None,
) -> Iterable[MobilizonEvent]:
    return map(
        MobilizonEvent.from_model,
        await prefetch_event_relations(
            _add_date_window(Event.all(), "begin_datetime", from_date, to_date)
        ),
    )


async def prefetch_event_relations(queryset: QuerySet[Event]) -> list[Event]:
    return (
        await queryset.prefetch_related("publications__publisher")
        .order_by("begin_datetime")
        .distinct()
    )


def _add_date_window(
    query,
    field_name: str,
    from_date: Optional[Arrow] = None,
    to_date: Optional[Arrow] = None,
):
    if from_date:
        query = query.filter(**{f"{field_name}__gt": from_date.to("utc").datetime})
    if to_date:
        query = query.filter(**{f"{field_name}__lt": to_date.to("utc").datetime})
    return query


@atomic(CONNECTION_NAME)
async def publications_with_status(
    status: PublicationStatus,
    event_mobilizon_id: Optional[UUID] = None,
    from_date: Optional[Arrow] = None,
    to_date: Optional[Arrow] = None,
) -> Dict[UUID, Publication]:
    query = Publication.filter(status=status)

    if event_mobilizon_id:
        query = query.prefetch_related("event").filter(
            event__mobilizon_id=event_mobilizon_id
        )

    query = _add_date_window(query, "timestamp", from_date, to_date)

    publications_list = (
        await query.prefetch_related("publisher").order_by("timestamp").distinct()
    )
    return {pub.id: pub for pub in publications_list}


async def events_without_publications(
    from_date: Optional[Arrow] = None, to_date: Optional[Arrow] = None,
) -> Iterable[MobilizonEvent]:
    query = Event.filter(publications__id=None)

    return map(
        MobilizonEvent.from_model,
        await prefetch_event_relations(
            _add_date_window(query, "begin_datetime", from_date, to_date)
        ),
    )