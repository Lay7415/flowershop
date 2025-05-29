# catalog/views.py
from django.shortcuts import render, get_object_or_404
from django.views import generic
from django.db.models import Q
from .models import Bouquet

from core.decorators import deny_roles

@deny_roles(["courier", "florist"])
def bouquet_list_view(request):
    bouquets = Bouquet.objects.filter(is_active=True)
    query = request.GET.get("q")
    if query:
        bouquets = bouquets.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(flower_items__flower__name__icontains=query)
        ).distinct()
    sort = request.GET.get("sort")
    if sort == "price_asc":
        bouquets = bouquets.order_by("price")
    elif sort == "price_desc":
        bouquets = bouquets.order_by("-price")
    else:
        bouquets = bouquets.order_by("name")
    context = {
        "bouquets": bouquets,
        "current_query": query or "",
        "current_sort": sort or "",
    }
    return render(request, "catalog/bouquet_list.html", context)

@deny_roles(["courier", "florist"])
def bouquet_detail_view(request, pk):
    bouquet = get_object_or_404(
        Bouquet.objects.filter(is_active=True).prefetch_related(
            "flower_items__flower", "ribbon_items__ribbon", "wrapper_items__wrapper"
        ),
        pk=pk,
    )
    return render(request, "catalog/bouquet_detail.html", {"bouquet": bouquet})
