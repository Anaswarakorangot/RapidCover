"""
Collusion Detection Service

Detects coordinated fraud attempts through:
1. Timing correlation - Multiple claims within same time window
2. Location clustering - Overlapping GPS patterns across partners
3. Network effects - Shared devices, IPs, or device fingerprints

Used by fraud queue endpoint to identify collusion rings.
"""

from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Dict, Tuple
import json

from app.models.claim import Claim, ClaimStatus
from app.models.partner import Partner
from app.models.fraud import PartnerDevice, PartnerGPSPing
from app.models.policy import Policy
from app.models.trigger_event import TriggerEvent
from app.utils.time_utils import utcnow


class CollusionRing:
    """Represents a detected collusion ring."""

    def __init__(
        self,
        ring_id: str,
        partner_ids: List[int],
        claim_ids: List[int],
        collusion_type: str,
        confidence: float,
        evidence: dict
    ):
        self.ring_id = ring_id
        self.partner_ids = partner_ids
        self.claim_ids = claim_ids
        self.collusion_type = collusion_type
        self.confidence = confidence
        self.evidence = evidence

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "ring_id": self.ring_id,
            "partner_ids": self.partner_ids,
            "claim_ids": self.claim_ids,
            "collusion_type": self.collusion_type,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "severity": "high" if self.confidence > 0.8 else ("medium" if self.confidence > 0.5 else "low")
        }


def detect_timing_correlation(
    db: Session,
    time_window_minutes: int = 30,
    min_claims: int = 3
) -> List[CollusionRing]:
    """
    Detect claims submitted within a tight time window.

    Args:
        db: Database session
        time_window_minutes: Time window to check (default 30 minutes)
        min_claims: Minimum number of claims to flag as collusion (default 3)

    Returns:
        List of detected collusion rings
    """
    rings = []

    # Get all pending/recent claims
    cutoff_time = utcnow() - timedelta(days=7)
    claims = db.query(Claim).filter(
        Claim.created_at >= cutoff_time,
        Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.APPROVED])
    ).order_by(Claim.created_at).all()

    # Sliding window to find clusters
    for i in range(len(claims)):
        window_end = claims[i].created_at + timedelta(minutes=time_window_minutes)
        clustered_claims = [claims[i]]

        for j in range(i + 1, len(claims)):
            if claims[j].created_at <= window_end:
                clustered_claims.append(claims[j])
            else:
                break

        if len(clustered_claims) >= min_claims:
            # Extract partner IDs (avoiding duplicates)
            partner_ids = list(set([
                db.query(Claim).join(Claim.policy).filter(Claim.id == c.id).first().policy.partner_id
                for c in clustered_claims
            ]))

            if len(partner_ids) >= min_claims:
                # Calculate confidence based on:
                # - Number of claims in window
                # - Uniqueness of partners
                # - Time concentration
                time_spread = (clustered_claims[-1].created_at - clustered_claims[0].created_at).total_seconds()
                confidence = min(
                    0.4 + (len(clustered_claims) * 0.1) + (0.3 if time_spread < 600 else 0.1),
                    1.0
                )

                rings.append(CollusionRing(
                    ring_id=f"timing_{claims[i].id}_{len(clustered_claims)}",
                    partner_ids=partner_ids,
                    claim_ids=[c.id for c in clustered_claims],
                    collusion_type="timing_correlation",
                    confidence=round(confidence, 2),
                    evidence={
                        "window_start": clustered_claims[0].created_at.isoformat(),
                        "window_end": clustered_claims[-1].created_at.isoformat(),
                        "time_spread_seconds": int(time_spread),
                        "claims_in_window": len(clustered_claims),
                        "unique_partners": len(partner_ids)
                    }
                ))

    return rings


def detect_location_clustering(
    db: Session,
    distance_threshold_km: float = 0.5,
    min_partners: int = 3
) -> List[CollusionRing]:
    """
    Detect partners with overlapping GPS patterns.

    Args:
        db: Database session
        distance_threshold_km: Maximum distance to consider as clustered
        min_partners: Minimum partners in cluster to flag

    Returns:
        List of detected collusion rings
    """
    from math import radians, cos, sin, asin, sqrt

    def haversine(lon1, lat1, lon2, lat2):
        """Calculate distance between two GPS points in km."""
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c
        return km

    rings = []

    # Get recent claims with GPS pings
    cutoff_time = utcnow() - timedelta(days=7)
    claims = db.query(Claim).filter(
        Claim.created_at >= cutoff_time,
        Claim.status == ClaimStatus.PENDING
    ).all()

    if not claims:
        return rings

    # Get GPS centroids for each partner with recent claims
    partner_centroids = {}
    for claim in claims:
        partner_id = claim.policy.partner_id

        if partner_id not in partner_centroids:
            # Get recent GPS pings (last 7 days)
            pings = db.query(PartnerGPSPing).filter(
                PartnerGPSPing.partner_id == partner_id,
                PartnerGPSPing.created_at >= cutoff_time
            ).limit(50).all()

            if pings:
                avg_lat = sum(p.lat for p in pings) / len(pings)
                avg_lng = sum(p.lng for p in pings) / len(pings)
                partner_centroids[partner_id] = (avg_lat, avg_lng, [claim.id])
            else:
                partner_centroids[partner_id] = (None, None, [claim.id])
        else:
            partner_centroids[partner_id][2].append(claim.id)

    # Find clusters
    processed = set()
    for pid1, (lat1, lng1, claims1) in partner_centroids.items():
        if pid1 in processed or lat1 is None:
            continue

        cluster = {pid1: claims1}

        for pid2, (lat2, lng2, claims2) in partner_centroids.items():
            if pid2 == pid1 or pid2 in processed or lat2 is None:
                continue

            dist = haversine(lng1, lat1, lng2, lat2)
            if dist <= distance_threshold_km:
                cluster[pid2] = claims2

        if len(cluster) >= min_partners:
            all_claim_ids = [cid for claim_list in cluster.values() for cid in claim_list]
            confidence = min(0.5 + (len(cluster) * 0.1), 1.0)

            rings.append(CollusionRing(
                ring_id=f"location_{pid1}_{len(cluster)}",
                partner_ids=list(cluster.keys()),
                claim_ids=all_claim_ids,
                collusion_type="location_clustering",
                confidence=round(confidence, 2),
                evidence={
                    "cluster_size": len(cluster),
                    "distance_threshold_km": distance_threshold_km,
                    "note": f"{len(cluster)} partners with GPS centroids within {distance_threshold_km}km"
                }
            ))

            processed.update(cluster.keys())

    return rings


def detect_network_effects(
    db: Session,
    min_shared_devices: int = 2
) -> List[CollusionRing]:
    """
    Detect partners sharing devices or device fingerprints.

    Args:
        db: Database session
        min_shared_devices: Minimum shared devices to flag

    Returns:
        List of detected collusion rings
    """
    rings = []

    # Get recent claims
    cutoff_time = utcnow() - timedelta(days=7)
    claims = db.query(Claim).filter(
        Claim.created_at >= cutoff_time,
        Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.APPROVED])
    ).all()

    if not claims:
        return rings

    partner_ids = list(set([c.policy.partner_id for c in claims]))

    # Build device sharing map
    device_to_partners = {}

    for partner_id in partner_ids:
        devices = db.query(PartnerDevice).filter(
            PartnerDevice.partner_id == partner_id
        ).all()

        for device in devices:
            # Use device ID and model as fingerprint
            fingerprint = f"{device.device_id}_{device.model}_{device.os_version}"

            if fingerprint not in device_to_partners:
                device_to_partners[fingerprint] = set()

            device_to_partners[fingerprint].add(partner_id)

    # Find shared devices
    for fingerprint, partners in device_to_partners.items():
        if len(partners) >= min_shared_devices:
            # Get claims for these partners
            partner_claims = db.query(Claim).join(Claim.policy).filter(
                Claim.created_at >= cutoff_time,
                Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.APPROVED]),
                Claim.policy.has(partner_id__in=list(partners))
            ).all()

            if partner_claims:
                confidence = min(0.6 + (len(partners) * 0.15), 1.0)

                rings.append(CollusionRing(
                    ring_id=f"network_{hash(fingerprint) % 100000}",
                    partner_ids=list(partners),
                    claim_ids=[c.id for c in partner_claims],
                    collusion_type="network_effects",
                    confidence=round(confidence, 2),
                    evidence={
                        "shared_device_fingerprint": fingerprint,
                        "partners_sharing": len(partners),
                        "note": f"{len(partners)} partners using same device fingerprint"
                    }
                ))

    return rings


def detect_all_collusion_rings(db: Session) -> List[CollusionRing]:
    """
    Run all collusion detection algorithms.

    Returns:
        Combined list of all detected collusion rings
    """
    all_rings = []

    # Timing correlation
    timing_rings = detect_timing_correlation(db)
    all_rings.extend(timing_rings)

    # Location clustering
    location_rings = detect_location_clustering(db)
    all_rings.extend(location_rings)

    # Network effects
    network_rings = detect_network_effects(db)
    all_rings.extend(network_rings)

    # Sort by confidence (highest first)
    all_rings.sort(key=lambda r: r.confidence, reverse=True)

    return all_rings


def get_collusion_summary(rings: List[CollusionRing]) -> dict:
    """Generate summary statistics for detected collusion rings."""
    if not rings:
        return {
            "total_rings": 0,
            "total_partners_flagged": 0,
            "total_claims_flagged": 0,
            "by_type": {},
            "by_severity": {"high": 0, "medium": 0, "low": 0}
        }

    all_partners = set()
    all_claims = set()
    by_type = {}
    by_severity = {"high": 0, "medium": 0, "low": 0}

    for ring in rings:
        all_partners.update(ring.partner_ids)
        all_claims.update(ring.claim_ids)

        # Count by type
        if ring.collusion_type not in by_type:
            by_type[ring.collusion_type] = 0
        by_type[ring.collusion_type] += 1

        # Count by severity
        severity = "high" if ring.confidence > 0.8 else ("medium" if ring.confidence > 0.5 else "low")
        by_severity[severity] += 1

    return {
        "total_rings": len(rings),
        "total_partners_flagged": len(all_partners),
        "total_claims_flagged": len(all_claims),
        "by_type": by_type,
        "by_severity": by_severity
    }
