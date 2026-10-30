from django.urls import path

from . import views

urlpatterns = [
    path('demand-prediction/', views.DemandPredictionView.as_view(), name='ai-demand'),
    path('price-recommendation/', views.PriceRecommendationView.as_view(), name='ai-price'),
    path('model-info/', views.ModelInfoView.as_view(), name='ai-model-info'),
    path('history/', views.PredictionHistoryView.as_view(), name='ai-history'),
]
