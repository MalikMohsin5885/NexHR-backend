# api/pagination.py
from rest_framework.pagination import PageNumberPagination

class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10  # default
    page_size_query_param = 'page_size'  # allows clients to pass `?page_size=6`
    max_page_size = 100
