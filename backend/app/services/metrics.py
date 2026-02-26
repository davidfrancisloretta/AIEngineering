from sqlalchemy.orm import Session

from models import CampaignMetrics
from schemas import MetricCreate, MetricUpdate


def _compute_rates(
    impressions: int, clicks: int, views: int, conversions: int
) -> tuple[float, float, float]:
    ttr = clicks / impressions
    vtr = views / impressions
    cvr = conversions / impressions
    return ttr, vtr, cvr


def create_metric(db: Session, data: MetricCreate) -> CampaignMetrics:
    ttr, vtr, cvr = _compute_rates(
        data.impressions, data.clicks, data.views, data.conversions
    )
    metric = CampaignMetrics(
        campaign_name=data.campaign_name,
        impressions=data.impressions,
        clicks=data.clicks,
        views=data.views,
        conversions=data.conversions,
        ttr=ttr,
        vtr=vtr,
        cvr=cvr,
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


def get_metric(db: Session, metric_id: int) -> CampaignMetrics | None:
    return db.query(CampaignMetrics).filter(CampaignMetrics.id == metric_id).first()


def get_all_metrics(db: Session) -> list[CampaignMetrics]:
    return db.query(CampaignMetrics).all()


def update_metric(
    db: Session, metric_id: int, data: MetricUpdate
) -> CampaignMetrics | None:
    metric = get_metric(db, metric_id)
    if not metric:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(metric, field, value)

    ttr, vtr, cvr = _compute_rates(
        metric.impressions, metric.clicks, metric.views, metric.conversions
    )
    metric.ttr = ttr
    metric.vtr = vtr
    metric.cvr = cvr

    db.commit()
    db.refresh(metric)
    return metric


def delete_metric(db: Session, metric_id: int) -> bool:
    metric = get_metric(db, metric_id)
    if not metric:
        return False
    db.delete(metric)
    db.commit()
    return True
