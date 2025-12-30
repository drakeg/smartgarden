from __future__ import annotations

import json
import secrets

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .device_templates import get_device_template, try_load_svg_and_map
from .forms import GardenForm, PodForm, PodNoteForm
from .models import Garden, Pod, PodNote
from .models import GlobalNote
from .forms import GlobalNoteForm

EXPORT_VERSION = 1

# Common route / template constants to avoid duplicated literals
GARDENS_HOME = "gardens:home"
GARDEN_LIST = "gardens:garden_list"
GARDEN_DETAIL = "gardens:garden_detail"
GARDENS_LOGIN = "gardens:login"
PARTIAL_POD_PANEL = "gardens/partials/pod_panel.html"
GARDEN_IMPORT_JSON = "gardens:garden_import_json"
GARDEN_GLOBAL_NOTES = "gardens:global_notes"
PARTIAL_GLOBAL_NOTES_LIST = "gardens/partials/global_notes_list.html"

# ---------------------------
# Guest Mode Configuration
# ---------------------------
GUEST_COOKIE_NAME = "sg_guest"
GUEST_MAX_GARDENS = 1
GUEST_MAX_NOTES_TOTAL = 25
GUEST_ALLOW_PUBLIC_LINK = False  # set True later if you want guests to share

# ---------------------------
# Helpers (OK to keep here for MVP)
# ---------------------------
def _get_guest_token(request) -> str | None:
    tok = request.COOKIES.get(GUEST_COOKIE_NAME)
    if not tok:
        return None
    if len(tok) > 64:
        return None
    return tok

def _can_edit_garden(request, garden: Garden) -> bool:
    # Logged-in owner
    if request.user.is_authenticated and garden.owner_id == request.user.id:
        return True

    # Guest ownership via cookie token
    tok = _get_guest_token(request)
    if tok and garden.is_guest and garden.guest_token == tok:
        return True

    return False

def _get_editable_garden_or_404(request, garden_id: int) -> Garden:
    garden = Garden.objects.filter(id=garden_id).first()
    if not garden or not _can_edit_garden(request, garden):
        raise Http404("Garden not found.")
    return garden

def _guest_notes_remaining(garden: Garden) -> int:
    total = PodNote.objects.filter(pod__garden=garden).count()
    return max(0, GUEST_MAX_NOTES_TOTAL - total)

def _garden_to_export_dict(garden: Garden) -> dict:
    pods_payload: list[dict] = []
    for pod in garden.pods.all().order_by("position"):
        notes_payload: list[dict] = []
        for n in pod.notes.all().order_by("created_at"):
            notes_payload.append({
                "created_at": n.created_at.isoformat(),
                "note": n.note,
                # Photos intentionally omitted in MVP export
                # "photo": n.photo.url if n.photo else None,
            })

        pods_payload.append({
            # Common route / template constants to avoid duplicated literals
            "position": pod.position,
            "plant_name": pod.plant_name,
            "planted_at": pod.planted_at.isoformat() if pod.planted_at else None,
            "status": pod.status,
            "notes": notes_payload,
        })

    return {
        "version": EXPORT_VERSION,
        "device_type": garden.device_type,
        "garden_name": garden.name,
        "exported_at": timezone.now().isoformat(),
        "pods": pods_payload,
    }


# ---------------------------
# Import helpers
# ---------------------------
def _parse_import_upload(upload) -> dict:
    try:
        raw = upload.read().decode("utf-8")
        return json.loads(raw)
    except Exception:
        raise ValueError("That file is not valid JSON.")


def _validate_import_data(data: dict) -> tuple[str, str, list]:
    if not isinstance(data, dict) or data.get("version") != EXPORT_VERSION:
        raise ValueError(f"Unsupported export version. Expected version={EXPORT_VERSION}.")

    garden_name = (data.get("garden_name") or "Imported Garden").strip()[:120]
    device_type = (data.get("device_type") or "GENERIC_12").strip()

    pods_data = data.get("pods") or []
    if not isinstance(pods_data, list) or len(pods_data) == 0:
        raise ValueError("Import file has no pods.")

    return garden_name, device_type, pods_data


def _create_garden_from_import(user, garden_name: str, device_type: str) -> tuple[Garden, int]:
    garden = Garden.objects.create(
        owner=user,
        is_guest=False,
        guest_token="",
        name=garden_name,
        device_type=device_type,
    )
    template = get_device_template(device_type)
    template_count = template.pod_count if template else 12
    return garden, template_count


def _get_pod_position(item: dict) -> int | None:
    try:
        pos = int(item.get("position"))
    except Exception:
        return None
    if pos < 1:
        return None
    return pos


def _apply_notes_to_pod(pod: Pod, notes: list) -> None:
    if not isinstance(notes, list):
        return
    for n in notes:
        note_text = (n.get("note") or "").strip()
        if not note_text:
            continue

        created_at_raw = n.get("created_at")
        created_at = timezone.now()
        if created_at_raw:
            try:
                created_at = timezone.datetime.fromisoformat(created_at_raw)
                if timezone.is_naive(created_at):
                    created_at = timezone.make_aware(created_at)
            except Exception:
                created_at = timezone.now()

        note_obj = PodNote.objects.create(pod=pod, note=note_text)
        PodNote.objects.filter(id=note_obj.id).update(created_at=created_at)


def _apply_single_pod(garden_obj: Garden, item: dict) -> None:
    pos = _get_pod_position(item)
    if pos is None:
        return

    pod, _created = Pod.objects.get_or_create(garden=garden_obj, position=pos)

    pod.plant_name = (item.get("plant_name") or "")[:120]

    planted_at = item.get("planted_at")
    pod.planted_at = None
    if planted_at:
        try:
            pod.planted_at = timezone.datetime.fromisoformat(planted_at).date()
        except Exception:
            pod.planted_at = None

    status = item.get("status")
    if status:
        pod.status = status[:20]
    pod.save()

    notes = item.get("notes") or []
    _apply_notes_to_pod(pod, notes)


def _apply_imported_pods(garden_obj: Garden, pods_list: list[dict]) -> None:
    for pod_item in pods_list:
        _apply_single_pod(garden_obj, pod_item)

# ---------------------------
# Auth + Home
# ---------------------------
@require_http_methods(["GET", "POST"])
def home(request):
    # If user is authenticated, show their gardens and a global notes area on the homepage.
    if request.user.is_authenticated:
        # Handle new global note submission from home page
        if request.method == "POST":
            form = GlobalNoteForm(request.POST)
            if form.is_valid():
                note = form.save(commit=False)
                note.author = request.user
                note.save()
                return redirect(GARDENS_HOME)
        else:
            form = GlobalNoteForm()

        gardens = Garden.objects.filter(owner=request.user).order_by("-created_at")
        notes = GlobalNote.objects.all().order_by("-created_at")[:50]
        return render(request, "gardens/home.html", {"gardens": gardens, "notes": notes, "form": form})

    # Unauthenticated visitors: marketing / guest CTA
    return render(request, "gardens/home.html")

def login_view(request): 
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(GARDEN_LIST)
        return render(request, "gardens/login.html", {"error": "Invalid username or password."})
    return render(request, "gardens/login.html")

def logout_view(request):
    logout(request)
    return redirect(GARDENS_HOME)

# ---------------------------
# Guest Mode: "Try it now"
# ---------------------------
@require_http_methods(["GET"])
def guest_start(request):
    """
    Create (or re-open) a guest garden tied to a cookie token.
    """
    if request.user.is_authenticated:
            return redirect(GARDEN_LIST)

    tok = _get_guest_token(request)
    if not tok:
        tok = secrets.token_urlsafe(24)

    existing = Garden.objects.filter(is_guest=True, guest_token=tok).order_by("-created_at")
    if existing.exists():
        resp = redirect(GARDEN_DETAIL, garden_id=existing.first().id)
        resp.set_cookie(GUEST_COOKIE_NAME, tok, max_age=60 * 60 * 24 * 90, httponly=True, samesite="Lax")
        return resp

    # Enforce max guest gardens (per browser token)
    if existing.count() >= GUEST_MAX_GARDENS:
        resp = redirect(GARDEN_DETAIL, garden_id=existing.first().id)
        resp.set_cookie(GUEST_COOKIE_NAME, tok, max_age=60 * 60 * 24 * 90, httponly=True, samesite="Lax")
        return resp

    # Create new guest garden
    garden = Garden.objects.create(
        owner=None,
        is_guest=True,
        guest_token=tok,
        name="Guest Garden",
        device_type="AHOPEGARDEN_12",
    )
    for pos in range(1, 13):
        Pod.objects.create(garden=garden, position=pos)

    resp = redirect(GARDEN_DETAIL, garden_id=garden.id)
    resp.set_cookie(GUEST_COOKIE_NAME, tok, max_age=60 * 60 * 24 * 90, httponly=True, samesite="Lax")
    return resp

# ---------------------------
# Gardens (Account-only list/create)
# ---------------------------
@require_http_methods(["GET", "POST"])
def garden_list(request):
    if not request.user.is_authenticated:
        return redirect(GARDENS_HOME)

    # Allow creating a GlobalNote from the gardens list page
    if request.method == "POST":
        form = GlobalNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.author = request.user
            note.save()
            return redirect(GARDEN_LIST)
    else:
        form = GlobalNoteForm()

    gardens = Garden.objects.filter(owner=request.user).order_by("-created_at")
    notes = GlobalNote.objects.all().order_by("-created_at")[:50]
    return render(request, "gardens/garden_list.html", {"gardens": gardens, "notes": notes, "form": form})

@require_http_methods(["GET", "POST"])
def garden_create(request):
    if not request.user.is_authenticated:
        return redirect(GARDENS_LOGIN)

    if request.method == "POST":
        form = GardenForm(request.POST)
        if form.is_valid():
            garden = form.save(commit=False)
            garden.owner = request.user
            # Ensure this is not treated as guest
            garden.is_guest = False
            garden.guest_token = ""
            garden.save()

            # Create template pods (12 for now)
            for pos in range(1, 13):
                Pod.objects.create(garden=garden, position=pos)

            return redirect(GARDEN_DETAIL, garden_id=garden.id)
    else:
        form = GardenForm()

    return render(request, "gardens/garden_create.html", {"form": form})

# ---------------------------
# Garden Detail (Owner OR Guest)
# ---------------------------
@require_http_methods(["GET"])
def garden_detail(request, garden_id: int):
    garden = _get_editable_garden_or_404(request, garden_id)

    device = get_device_template(garden.device_type)
    svg_text, pod_map = try_load_svg_and_map(device)

    # Portrait orientation: front/back is LEFT/RIGHT.
    # Preference is stored per garden (Garden.view_front = "left" or "right")
    front = getattr(garden, "view_front", None) or "left"

    pods = list(garden.pods.all().order_by("position"))

    # Build rows for grid fallback (3 columns x 4 rows for Ahopegarden 12)
    # If you later add other devices, put cols on the template or infer from device.
    cols = 3
    rows = [pods[i:i + cols] for i in range(0, len(pods), cols)]

    # If front is right, flip each row right<->left (portrait flip)
    if front == "right":
        rows = [list(reversed(r)) for r in rows]

    return render(request, "gardens/garden_detail.html", {
        "garden": garden,
        "pods": pods,                 # still available for SVG / other uses
        "grid_rows": rows,            # use this in grid fallback loop
        "device": device,
        "svg_text": svg_text,
        "pod_map": pod_map,
        "today": timezone.localdate(),
        "is_guest": garden.is_guest,
        "guest_notes_remaining": _guest_notes_remaining(garden) if garden.is_guest else None,
        "front": front,               # "left" or "right"
    })

# ---------------------------
# Pod Side Panel (Owner OR Guest)
# ---------------------------
@require_http_methods(["GET"])
def pod_panel(request, garden_id: int, position: int):
    garden = _get_editable_garden_or_404(request, garden_id)
    pod = get_object_or_404(Pod, garden=garden, position=position)

    pod_form = PodForm(instance=pod)
    note_form = PodNoteForm()

    return render(request, PARTIAL_POD_PANEL, {
        "garden": garden,
        "pod": pod,
        "pod_form": pod_form,
        "note_form": note_form,
        "today": timezone.localdate(),
        "is_guest": garden.is_guest,
        "guest_notes_remaining": _guest_notes_remaining(garden) if garden.is_guest else None,
    })

@require_http_methods(["POST"])
def pod_save(request, garden_id: int, position: int):
    garden = _get_editable_garden_or_404(request, garden_id)
    pod = get_object_or_404(Pod, garden=garden, position=position)

    form = PodForm(request.POST, instance=pod)
    if form.is_valid():
        form.save()

    pod_form = PodForm(instance=pod)
    note_form = PodNoteForm()
    return render(request, PARTIAL_POD_PANEL, {
        "garden": garden,
        "pod": pod,
        "pod_form": pod_form,
        "note_form": note_form,
        "today": timezone.localdate(),
        "is_guest": garden.is_guest,
        "guest_notes_remaining": _guest_notes_remaining(garden) if garden.is_guest else None,
    })

@require_http_methods(["POST"])
def pod_note_add(request, garden_id: int, position: int):
    garden = _get_editable_garden_or_404(request, garden_id)
    pod = get_object_or_404(Pod, garden=garden, position=position)

    # Enforce guest notes cap
    if garden.is_guest and _guest_notes_remaining(garden) <= 0:
        pod_form = PodForm(instance=pod)
        note_form = PodNoteForm()
        return render(request, PARTIAL_POD_PANEL, {
            "garden": garden,
            "pod": pod,
            "pod_form": pod_form,
            "note_form": note_form,
            "today": timezone.localdate(),
            "error": "Guest mode limit reached (notes). Create an account to unlock more.",
            "is_guest": True,
            "guest_notes_remaining": 0,
        })

    form = PodNoteForm(request.POST, request.FILES)
    if form.is_valid():
        note = form.save(commit=False)
        note.pod = pod
        note.save()

    pod_form = PodForm(instance=pod)
    note_form = PodNoteForm()
    return render(request, PARTIAL_POD_PANEL, {
        "garden": garden,
        "pod": pod,
        "pod_form": pod_form,
        "note_form": note_form,
        "today": timezone.localdate(),
        "is_guest": garden.is_guest,
        "guest_notes_remaining": _guest_notes_remaining(garden) if garden.is_guest else None,
    })

# (flip view removed)
# ---------------------------
# Sharing
# ---------------------------
@require_http_methods(["POST"])
def garden_toggle_public(request, garden_id: int):
    garden = _get_editable_garden_or_404(request, garden_id)

    if garden.is_guest and not GUEST_ALLOW_PUBLIC_LINK:
        messages.error(request, "Guest gardens cannot be shared publicly. Create an account to enable sharing.")
        return redirect(GARDEN_DETAIL, garden_id=garden.id)

    garden.is_public = not garden.is_public

    if garden.is_public:
        garden.ensure_share_slug()  # this saves share_slug if needed

    # Save only the public flag (and nothing else)
    garden.save(update_fields=["is_public"])

    return redirect(GARDEN_DETAIL, garden_id=garden.id)

@require_http_methods(["GET"])
def garden_public(request, share_slug: str):
    garden = get_object_or_404(Garden, share_slug=share_slug, is_public=True)
    pods = list(garden.pods.all())
    return render(request, "gardens/garden_public.html", {"garden": garden, "pods": pods})

# ---------------------------
# Export / Import (Account-only)
# ---------------------------
@require_http_methods(["GET"])
def garden_export_json(request, garden_id: int):
    if not request.user.is_authenticated:
        return redirect(GARDENS_LOGIN)

    garden = Garden.objects.filter(id=garden_id, owner=request.user).first()
    if not garden:
        raise Http404("Garden not found.")

    payload = _garden_to_export_dict(garden)
    filename = f"{garden.name.strip().replace(' ', '_')}_export.json"
    resp = JsonResponse(payload, json_dumps_params={"indent": 2})
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp

@require_http_methods(["GET", "POST"])
def garden_import_json(request):
    if not request.user.is_authenticated:
        return redirect(GARDENS_LOGIN)

    if request.method == "GET":
        return render(request, "gardens/garden_import.html")

    upload = request.FILES.get("import_file")
    if not upload:
        messages.error(request, "Please choose a JSON file to import.")
        return redirect(GARDEN_IMPORT_JSON)

    try:
        raw = upload.read().decode("utf-8")
        data = json.loads(raw)
    except Exception:
        messages.error(request, "That file is not valid JSON.")
        return redirect(GARDEN_IMPORT_JSON)

    if not isinstance(data, dict) or data.get("version") != EXPORT_VERSION:
        messages.error(request, f"Unsupported export version. Expected version={EXPORT_VERSION}.")
        return redirect(GARDEN_IMPORT_JSON)

    garden_name = (data.get("garden_name") or "Imported Garden").strip()[:120]
    device_type = (data.get("device_type") or "GENERIC_12").strip()

    pods_data = data.get("pods") or []
    if not isinstance(pods_data, list) or len(pods_data) == 0:
        messages.error(request, "Import file has no pods.")
        return redirect(GARDEN_IMPORT_JSON)

    # Create the garden under the user
    garden = Garden.objects.create(
        owner=request.user,
        is_guest=False,
        guest_token="",
        name=garden_name,
        device_type=device_type,
    )

    template = get_device_template(device_type)
    template_count = template.pod_count if template else 12

    # Create baseline pods 1..template_count
    for pos in range(1, template_count + 1):
        Pod.objects.create(garden=garden, position=pos)

    # Apply imported pod data
    _apply_imported_pods(garden, pods_data)

    messages.success(request, f"Imported garden: {garden.name}")
    return redirect(GARDEN_DETAIL, garden_id=garden.id)


# ---------------------------
# Global Notes UI
# ---------------------------
@require_http_methods(["GET", "POST"])
def global_notes_list_create(request):
    if not request.user.is_authenticated:
        return redirect(GARDENS_LOGIN)

    if request.method == "POST":
        form = GlobalNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.author = request.user
            note.save()
            return redirect(GARDEN_GLOBAL_NOTES)
    else:
        form = GlobalNoteForm()

    notes = GlobalNote.objects.all().order_by("-created_at")[:50]
    return render(request, "gardens/global_notes.html", {"notes": notes, "form": form})


@require_http_methods(["POST"])
def global_note_create(request):
    if not request.user.is_authenticated:
        return redirect(GARDENS_LOGIN)

    form = GlobalNoteForm(request.POST)
    if form.is_valid():
        note = form.save(commit=False)
        note.author = request.user
        note.save()

    # If HTMX request, return the updated list fragment
    if request.headers.get("HX-Request"):
        notes = GlobalNote.objects.all().order_by("-created_at")[:50]
        return render(request, PARTIAL_GLOBAL_NOTES_LIST, {"notes": notes})

    return redirect(request.META.get("HTTP_REFERER", GARDEN_GLOBAL_NOTES))


@require_http_methods(["POST", "DELETE"])
def global_note_delete(request, pk: int):
    if not request.user.is_authenticated:
        return redirect(GARDENS_LOGIN)

    note = get_object_or_404(GlobalNote, pk=pk)
    if note.author_id != request.user.id:
        return Http404("Not allowed")

    note.delete()
    if request.headers.get("HX-Request"):
        notes = GlobalNote.objects.all().order_by("-created_at")[:50]
        return render(request, PARTIAL_GLOBAL_NOTES_LIST, {"notes": notes})

    return redirect(request.META.get("HTTP_REFERER", GARDEN_GLOBAL_NOTES))


@require_http_methods(["GET", "POST"])
def global_note_edit(request, pk: int):
    if not request.user.is_authenticated:
        return redirect(GARDENS_LOGIN)

    note = get_object_or_404(GlobalNote, pk=pk)
    if note.author_id != request.user.id:
        return Http404("Not allowed")

    if request.method == "POST":
        form = GlobalNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            if request.headers.get("HX-Request"):
                notes = GlobalNote.objects.all().order_by("-created_at")[:50]
                return render(request, PARTIAL_GLOBAL_NOTES_LIST, {"notes": notes})
            return redirect(GARDEN_GLOBAL_NOTES)

    else:
        form = GlobalNoteForm(instance=note)

    if request.headers.get("HX-Request"):
        return render(request, "gardens/partials/global_note_form.html", {"form": form, "note": note})

    return render(request, "gardens/global_notes.html", {"form": form, "notes": GlobalNote.objects.all().order_by("-created_at")[:50]})