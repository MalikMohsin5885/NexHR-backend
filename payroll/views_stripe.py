import stripe
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now
from .models import Payroll, Payslip

stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    # ✅ Handle payment success
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        payroll_id = session.get("metadata", {}).get("payroll_id")

        if payroll_id:
            try:
                payroll = Payroll.objects.get(id=payroll_id)
                payroll.payment_status = "PAID"
                payroll.paid_on = now().date()
                payroll.save()

                # Create a Payslip (if not exists already)
                Payslip.objects.get_or_create(
                    payroll=payroll,
                    defaults={"payslip_pdf_url": f"https://dummy-payslips.com/{payroll.id}.pdf"}
                )

                print(f"✅ Payroll {payroll.id} marked as PAID and payslip generated")

            except Payroll.DoesNotExist:
                print(f"❌ Payroll {payroll_id} not found")

    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        print(f"❌ Payment failed: {payment_intent['id']}")

    return JsonResponse({"status": "success"})
