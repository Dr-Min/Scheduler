import os
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import date
import logging

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)

# 애플리케이션 초기화
app = Flask(__name__, static_folder='./build', static_url_path='')
app.logger.setLevel(logging.DEBUG)

# CORS 설정
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 데이터베이스 설정
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'scheduler.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 데이터베이스 초기화
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# 모델 정의
class Schedule(db.Model):
    __tablename__ = 'schedule'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)
    user = db.Column(db.String(50), nullable=False)
    checkInTime = db.Column(db.String(5))
    exercised = db.Column(db.Boolean, default=False)
    reflection = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date,
            'user': self.user,
            'checkInTime': self.checkInTime,
            'exercised': self.exercised,
            'reflection': self.reflection
        }

# 데이터베이스 생성
with app.app_context():
    db.create_all()

# API 라우트
@app.route('/api/schedules', methods=['GET'])
def get_schedules():
    app.logger.debug("Fetching all schedules")
    try:
        schedules = Schedule.query.all()
        return jsonify([schedule.to_dict() for schedule in schedules])
    except Exception as e:
        app.logger.error(f"Error fetching schedules: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/schedules', methods=['POST'])
def add_schedule():
    app.logger.debug("Adding new schedule")
    try:
        data = request.json
        new_schedule = Schedule(
            date=data['date'],
            user=data['user'],
            checkInTime=data.get('checkInTime'),
            exercised=data.get('exercised', False),
            reflection=data.get('reflection')
        )
        db.session.add(new_schedule)
        db.session.commit()
        return jsonify(new_schedule.to_dict()), 201
    except Exception as e:
        app.logger.error(f"Error adding schedule: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/schedules/<int:id>', methods=['PUT'])
def update_schedule(id):
    app.logger.debug(f"Updating schedule with id {id}")
    try:
        schedule = Schedule.query.get_or_404(id)
        data = request.json
        schedule.checkInTime = data.get('checkInTime', schedule.checkInTime)
        schedule.exercised = data.get('exercised', schedule.exercised)
        schedule.reflection = data.get('reflection', schedule.reflection)
        db.session.commit()
        return jsonify(schedule.to_dict())
    except Exception as e:
        app.logger.error(f"Error updating schedule: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/schedules/<string:user>/<string:date>', methods=['GET'])
def get_schedule(user, date):
    app.logger.debug(f"Fetching schedule for user {user} on date {date}")
    try:
        schedule = Schedule.query.filter_by(user=user, date=date).first()
        if schedule:
            return jsonify(schedule.to_dict())
        else:
            return jsonify({"message": "Schedule not found"}), 404
    except Exception as e:
        app.logger.error(f"Error fetching schedule: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/schedules/<string:user>', methods=['GET'])
def get_user_schedules(user):
    app.logger.debug(f"Fetching all schedules for user {user}")
    try:
        schedules = Schedule.query.filter_by(user=user).all()
        return jsonify([schedule.to_dict() for schedule in schedules])
    except Exception as e:
        app.logger.error(f"Error fetching user schedules: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 정적 파일 서빙
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    app.logger.debug(f"Serving path: {path}")
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# 테스트 라우트
@app.route('/test_db')
def test_db():
    try:
        db.session.execute(db.select(Schedule))
        return "Database connection successful"
    except Exception as e:
        return f"Database connection failed: {str(e)}"

# 오류 핸들러
@app.errorhandler(404)
def not_found(error):
    app.logger.error(f"404 error: {error}")
    return app.send_static_file('index.html')

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"500 error: {error}")
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500

#DB 다운 받아버려잇
@app.route('/api/download_db')
def download_db():
    try:
        today = date.today().strftime("%Y%m%d")
        db_path = os.path.join(basedir, 'scheduler.db')
        return send_file(db_path, as_attachment=True, download_name=f'scheduler_{today}.db')
    except Exception as e:
        app.logger.error(f"Error downloading database: {str(e)}")
        return jsonify({"error": "Failed to download database"}), 500

# 애플리케이션 실행
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.logger.info(f"Starting application on port {port}")
    app.run(host='0.0.0.0', port=port)