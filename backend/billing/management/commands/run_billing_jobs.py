from django.core.management.base import BaseCommand

from billing.services import reconcile_pending_payments, run_status_sync


class Command(BaseCommand):
    help = "Reconcilia PIX pendentes, inativa inadimplentes, envia lembretes e expira cobranças."

    def handle(self, *args, **options):
        confirmed = reconcile_pending_payments()
        result = run_status_sync()
        self.stdout.write(
            f"Confirmados na reconciliação: {confirmed} | Inativados: {result['deactivated']} | "
            f"Lembretes: {result['reminders']} | Cobranças expiradas: {result['expired_charges']}"
        )