from django.contrib import admin
from django.utils.translation import ugettext_lazy as _


class SoftDeletionAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = self.model.all_objects
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def delete_model(self, request, obj):
        obj.hard_delete()

    def delete_queryset(self, request, queryset):
        return queryset.hard_delete()


class SoftDeletionStatusFilter(admin.SimpleListFilter):
    title = _("Status de suppression par l'utilisateur")

    parameter_name = "deletion_status"

    def lookups(self, request, model_admin):
        return (
            (None, _("Active")),
            ("deleted", _("🗑️ Supprimée")),
            ("all", _("All")),
        )

    # need to override choices otherwise django adds 'all' as the
    # None value choice, whereas in this case None is 'Active'
    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                "selected": self.value() == lookup,
                "query_string": cl.get_query_string(
                    {
                        self.parameter_name: lookup,
                    },
                    [],
                ),
                "display": title,
            }

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset.filter(deletion_date=None)
        elif self.value() in ("all"):
            return queryset
        elif self.value() in ("deleted"):
            return queryset.filter(deletion_date__isnull=False)
