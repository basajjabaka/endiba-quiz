# Endiba Quiz

A comprehensive quiz web application built with Python (Flask) that allows users to take quizzes from Word documents and provides detailed analytics for administrators.

## Features

### User Features
- **Interactive Quiz Interface**: Click on answer options to select them
- **Progress Tracking**: See your progress as you answer questions
- **Instant Results**: Get your score immediately after submission
- **Color-Coded Feedback**:
  - Red (0-3/10): Needs improvement
  - Orange (4-6/10): Good effort
  - Green (7-10/10): Excellent!
- **Detailed Review**: Review your answers after completing the quiz
- **IP-based Prevention**: Prevents taking the quiz multiple times from the same IP

### Admin Features
- **Dashboard Statistics**:
  - Total quiz attempts
  - Completion rate percentage
  - Average time taken
- **Interactive Charts**:
  - Activity by hour of day
  - Score distribution
- **Question Analytics**:
  - Most answered correctly questions
  - Most answered wrongly questions
  - Per-question answer statistics
- **Document Upload**: Easy Word document upload for question management
- **Data Export**: Export quiz results to CSV

## Tech Stack

- **Backend**: Python 3.9+ with Flask
- **Database**: SQLite (development) / PostgreSQL (production)
- **Document Parsing**: python-docx
- **Data Visualization**: Plotly.js and Pandas
- **Frontend**: HTML5, TailwindCSS, Vanilla JavaScript
- **Deployment**: Gunicorn

## Project Structure

```
endiba_quiz/
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── models.py              # Database models
├── requirements.txt       # Python dependencies
├── create_sample_quiz.py  # Script to generate sample questions
├── utils/
│   └── parser.py          # Word document parser
├── static/
│   └── uploads/           # Uploaded files storage
├── templates/
│   ├── base.html          # Base template
│   ├── index.html         # Landing page
│   ├── quiz.html          # Quiz interface
│   ├── result.html        # Results page
│   ├── already_completed.html
│   ├── error.html
│   └── admin/
│       ├── login.html     # Admin login
│       ├── dashboard.html # Admin dashboard
│       └── upload.html    # Question upload
└── README.md
```

## Installation

1. **Clone or navigate to the project directory**:
   ```bash
   cd endiba_quiz
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**:
   ```bash
   flask init-db
   ```

5. **Run the application**:
   ```bash
   python app.py
   ```

6. **Access the application**:
   - Quiz: http://localhost:5000
   - Admin Dashboard: http://localhost:5000/admin/login

## Default Admin Credentials

- **Username**: admin
- **Password**: admin123

> **Note**: Change these credentials in production by setting environment variables:
> ```bash
> export ADMIN_USERNAME=your_username
> export ADMIN_PASSWORD=your_password
> ```

## Document Format

Upload Word documents (.docx) with the following format:

```
Question 1: What is the capital of France?
A. London
B. Paris
C. Berlin
D. Madrid
Question 1 Answer: B

Question 2: Your question here
A. Option A
B. Option B
C. Option C
D. Option D
Question 2 Answer: A

... and so on
```

## Generating Sample Questions

Run the provided script to create a sample quiz document:

```bash
python create_sample_quiz.py
```

This will create `sample_quiz.docx` with 10 sample questions that you can upload and test.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | Auto-generated |
| `DATABASE_URI` | Database connection URI | `sqlite:///endiba_quiz.db` |
| `ADMIN_USERNAME` | Admin username | `admin` |
| `ADMIN_PASSWORD` | Admin password | `admin123` |
| `IP_LOCK_ENABLED` | Enable IP-based prevention | `True` |

## Scaling for Production

For production deployment:

1. **Use PostgreSQL**:
   ```bash
   export DATABASE_URI=postgresql://user:password@localhost/endiba_quiz
   ```

2. **Use Gunicorn**:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

3. **Use a process manager** (systemd, supervisor, etc.)

4. **Configure reverse proxy** (Nginx, Apache)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Landing page |
| `/quiz` | GET | Quiz interface |
| `/submit` | POST | Submit quiz answers |
| `/result` | GET | Results page |
| `/admin/login` | GET/POST | Admin login |
| `/admin` | GET | Admin dashboard |
| `/admin/upload` | GET/POST | Upload questions |
| `/admin/export` | GET | Export CSV data |
| `/api/questions` | GET | Get questions (JSON) |
| `/api/stats` | GET | Get quick stats (JSON) |

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

MIT License

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
