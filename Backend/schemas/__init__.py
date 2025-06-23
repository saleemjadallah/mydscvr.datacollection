# Schemas package
from .events_schemas import (
    EventResponse, EventListResponse, SearchQuery, SearchFilters,
    UserEventCreate, UserEventResponse, SuccessResponse,
    SearchSuggestion, SearchSuggestionsResponse, SearchFiltersResponse
)

# Import user schemas if available
try:
    from .user_schemas import *
except ImportError:
    # User schemas not available, continue without them
    pass