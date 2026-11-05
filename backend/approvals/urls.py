from rest_framework.routers import DefaultRouter

from .views import ApprovalRequestViewSet, ApprovalRuleViewSet


router = DefaultRouter()

router.register(
    "approvals",
    ApprovalRequestViewSet,
    basename="approval",
)

router.register(
    "approval-rules",
    ApprovalRuleViewSet,
    basename="approval-rule",
)

urlpatterns = router.urls