import json
import requests
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.views.decorators.csrf import csrf_exempt

from .EmailBackend import EmailBackend
from .models import Attendance, Session, Subject

# Create your views here.

def login_page(request):
    if request.user.is_authenticated:
        if request.user.user_type == '1':
            return redirect(reverse("admin_home"))
        elif request.user.user_type == '2':
            return redirect(reverse("staff_home"))
        else:
            return redirect(reverse("student_home"))
    return render(request, 'main_app/login.html')

def doLogin(request, **kwargs):
    if request.method != 'POST':
        return HttpResponse("<h4>Denied</h4>")
    else:
        # Authenticate
        user = EmailBackend.authenticate(request, username=request.POST.get('email'), password=request.POST.get('password'))
        if user is not None:
            login(request, user)
            if user.user_type == '1':
                return redirect(reverse("admin_home"))
            elif user.user_type == '2':
                return redirect(reverse("staff_home"))
            else:
                return redirect(reverse("student_home"))
        else:
            messages.error(request, "Invalid details")
            return redirect("/")

def logout_user(request):
    if request.user is not None:
        logout(request)
    return redirect("/")

@csrf_exempt
def get_attendance(request):
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        session = get_object_or_404(Session, id=session_id)
        attendance = Attendance.objects.filter(subject=subject, session=session)
        attendance_list = []
        for attd in attendance:
            data = {
                    "id": attd.id,
                    "attendance_date": str(attd.date),
                    "session": attd.session.id
                    }
            attendance_list.append(data)
        return JsonResponse(json.dumps(attendance_list), safe=False)
    except Exception as e:
        return None

def showFirebaseJS(request):
    data = """
    // Give the service worker access to Firebase Messaging.
// Note that you can only use Firebase Messaging here, other Firebase libraries
// are not available in the service worker.
importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-messaging.js');

// Initialize the Firebase app in the service worker by passing in
// your app's Firebase config object.
// https://firebase.google.com/docs/web/setup#config-object
firebase.initializeApp({
    apiKey: "AIzaSyBarDWWHTfTMSrtc5Lj3Cdw5dEvjAkFwtM",
    authDomain: "sms-with-django.firebaseapp.com",
    databaseURL: "https://sms-with-django.firebaseio.com",
    projectId: "sms-with-django",
    storageBucket: "sms-with-django.appspot.com",
    messagingSenderId: "945324593139",
    appId: "1:945324593139:web:03fa99a8854bbd38420c86",
    measurementId: "G-2F2RXTL9GT"
});

// Retrieve an instance of Firebase Messaging so that it can handle background
// messages.
const messaging = firebase.messaging();
messaging.setBackgroundMessageHandler(function (payload) {
    const notification = JSON.parse(payload);
    const notificationOption = {
        body: notification.body,
        icon: notification.icon
    }
    return self.registration.showNotification(payload.notification.title, notificationOption);
});
    """
    return HttpResponse(data, content_type='application/javascript')

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Note
from .forms import NoteForm

@login_required
def add_note(request):
    if request.method == 'POST':
        form = NoteForm(request.POST, request.FILES)
        if form.is_valid():
            note = form.save(commit=False)
            note.staff = request.user.staff
            note.save()
            return redirect('note_list')
    else:
        form = NoteForm()
    return render(request, 'staff_template/add_note.html', {'form': form})

@login_required
def edit_note(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    if request.method == 'POST':
        form = NoteForm(request.POST, request.FILES, instance=note)
        if form.is_valid():
            form.save()
            return redirect('staff_template/note_list')
    else:
        form = NoteForm(instance=note)
    return render(request, 'staff_template/edit_note.html', {'form': form})

@login_required
def delete_note(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    note.delete()
    return redirect('note_list')

@login_required
def note_list(request):
    notes = Note.objects.filter(staff=request.user.staff)
    return render(request, 'staff_template/note_list.html', {'notes': notes})

@login_required
def student_note_list(request):
    notes = Note.objects.filter(student=request.user.student)
    return render(request, 'student_template/student_note_list.html', {'notes': notes})

import fitz  # PyMuPDF
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer

@login_required
def pdf_summarizer(request):
    if request.method == 'POST':
        pdf_file = request.FILES['pdf']
        pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
        text = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text += page.get_text()

        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summary = summarizer(parser.document, 5)  # Summarize to 5 sentences

        summarized_text = " ".join([str(sentence) for sentence in summary])
        return render(request, 'student_template/pdf_summarizer.html', {'summary': summarized_text})
    return render(request, 'student_template/pdf_summarizer.html')
from django.shortcuts import render
from django.http import JsonResponse
import requests

# Replace with your API key and URL
API_KEY = 'AIzaSyAfg0HCBWjOqgFLJhKkZFEox9yGiWJ4_Jk'
API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent'

# Define predefined responses for the chatbot
PREDEFINED_RESPONSES = {
    'hello': 'Hi there! How can I assist you today?',
    'bye': 'Goodbye! Have a great day!',
    # Add more predefined responses as needed
}

def chatbot(request):
    if request.method == 'POST':
        user_message = request.POST.get('message')
        conversation_history = request.session.get('conversation_history', [])

        # Append user message to the conversation history
        conversation_history.append(f"input: {user_message}")
        bot_reply = PREDEFINED_RESPONSES.get(user_message.lower(), None)  # Case insensitive match

        if not bot_reply:
            # Make a request to the Google API if the message is not predefined
            headers = {'Content-Type': 'application/json'}
            messages = [{'text': message} for message in conversation_history]

            data = {'contents': [{'parts': messages}]}

            try:
                response = requests.post(f'{API_URL}?key={API_KEY}', headers=headers, json=data)
                response.raise_for_status()
                api_response = response.json()
                bot_reply = api_response['candidates'][0]['content']['parts'][0]['text']
                bot_reply = '. '.join(bot_reply.split('. ')[:3])  # Limit response to 3 sentences
            except requests.RequestException as e:
                print(f"API request error: {e}")
                bot_reply = 'Sorry, there was an error processing your request.'

        # Append bot reply to conversation history
        conversation_history.append(f"output: {bot_reply}")
        request.session['conversation_history'] = conversation_history

        # Return the bot reply as a JSON response
        return JsonResponse({'reply': bot_reply})

    return render(request, 'chatbot.html')