import math

from engine.explainer import describe
from engine.history import HistoryStore, UserHistory
from engine.scorers.base import Scorer
from engine.types import LoginEvent, Reason

# Feature families, most specific level first. The interpolation weights are the ones the dataset
# authors fitted for this dataset (github.com/das-group/rba-algorithm, used in Wiefling et al. 2022).
FAMILIES = {
    "ip": {"ip": 0.6, "asn": 0.3, "country": 0.1},
    "user_agent": {"user_agent": 0.5386653840551359, "browser": 0.2680451498625666,
                   "os": 0.18818295100109536, "device_type": 0.0051065150812021525},
}
# From the reference implementation: a context the user has never shown at any level
# is treated as four times less likely for them than for the average user.
UNSEEN_LOCAL_DIVISOR = 4


class FreemanScorer(Scorer):
    """Freeman et al. (2016) Eq. 7 in log space: sum of log p(x)/p(x|u) per family, plus log p(u|A)/p(u|L)."""

    name = "freeman"

    def raw_score(self, event: LoginEvent, history: HistoryStore) -> tuple[float, list[Reason]]:
        user = history.get_user(event.user_id)
        log_score = 0.0
        reasons = []
        for family, weights in FAMILIES.items():
            local_p = local_likelihood(event, user, weights)
            if local_p == 0:
                term = math.log(UNSEEN_LOCAL_DIVISOR)  # exact, so identical evidence gives identical scores
            else:
                term = math.log(global_likelihood(event, history, weights)) - math.log(local_p)
            log_score += term
            if term > 0:
                reasons.append(Reason(f"UNUSUAL_{family.upper()}", family_text(family, event, user), term))

        # p(u|A) is uniform over users; p(u|L) is the user's share of logins, add-one smoothed for new users.
        # Both use training-period totals, like p(x), so the score doesn't drift as the service grows.
        users = max(len(history.global_freqs.users), 1)
        user_term = math.log(1 / users) - math.log((user.login_count + 1) / (history.global_freqs.total + users))
        log_score += user_term
        if user_term > 0:
            text = describe("prior_logins", event, user, {"prior_logins": user.login_count})
            reasons.append(Reason("SHORT_HISTORY", text, user_term))

        reasons.sort(key=lambda r: r.weight, reverse=True)
        return log_score, reasons


def global_likelihood(event: LoginEvent, history: HistoryStore, weights: dict[str, float]) -> float:
    # Eq. 9 and 11: each level estimates p(x) as p(x | level value) * p(level value), mixed with fixed weights.
    freqs = history.global_freqs
    top, *coarser = weights
    if freqs.count(top, getattr(event, top)):
        return freqs.freq(top, getattr(event, top))  # a seen value gets the same estimate at every level
    likelihood = weights[top] * freqs.freq(top, getattr(event, top))
    for level in coarser:
        # Eq. 8 inside the level: one unseen value next to the c values already seen there.
        seen_in_level = freqs.count(level, getattr(event, level))
        likelihood += weights[level] * seen_in_level / ((seen_in_level + 1) * (freqs.total + 1))
    return likelihood


def local_likelihood(event: LoginEvent, user: UserHistory, weights: dict[str, float]) -> float:
    # The user's own share of logins with this value at each level, mixed with the same weights.
    if user.login_count == 0:
        return 0.0
    return sum(w * user.seen[level][getattr(event, level)] for level, w in weights.items()) / user.login_count


def family_text(family: str, event: LoginEvent, user: UserHistory) -> str:
    for level in reversed(FAMILIES[family]):  # name the broadest level the user has never used
        if user.seen[level][getattr(event, level)] == 0:
            return describe(level, event, user, {})
    return "rarely used network for this user" if family == "ip" else "rarely used browser for this user"
