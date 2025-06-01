# catalog/views.py
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.views import generic
from django.db.models import Q
from .models import Bouquet

from core.decorators import deny_roles

@deny_roles(["courier", "florist"])
def bouquet_list_view(request):
    bouquets = Bouquet.objects.filter(is_active=True)
    
    # Search handling
    query = request.GET.get("q")
    if query:
        bouquets = bouquets.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(flower_items__flower__name__icontains=query) |
            Q(tag__icontains=query)
        ).distinct()
    
    # Price range filtering
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    if min_price:
        try:
            bouquets = bouquets.filter(price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            bouquets = bouquets.filter(price__lte=float(max_price))
        except ValueError:
            pass
    
    # Tag filtering
    tag = request.GET.get("tag")
    if tag:
        bouquets = bouquets.filter(tag=tag)

    # Sorting
    sort = request.GET.get("sort")
    if sort == "price_asc":
        bouquets = bouquets.order_by("price")
    elif sort == "price_desc":
        bouquets = bouquets.order_by("-price")
    else:
        bouquets = bouquets.order_by("name")
    
    # Pagination
    per_page = 12  # Number of items per page
    paginator = Paginator(bouquets, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get unique tags for filtering
    all_tags = Bouquet.objects.filter(is_active=True).values_list('tag', flat=True).distinct()
    
    context = {
        "page_obj": page_obj,
        "current_query": query or "",
        "current_sort": sort or "",
        "current_min_price": min_price or "",
        "current_max_price": max_price or "",
        "current_tag": tag or "",
        "all_tags": all_tags,
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
