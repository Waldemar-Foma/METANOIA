import json

class TestManager:
    def __init__(self, db):
        self.db = db
    
    def get_test_questions(self, question_type=None):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if question_type:
            cursor.execute('''
                SELECT id, question_text, options, correct_answer, explanation, question_type
                FROM test_questions WHERE question_type = ?
            ''', (question_type,))
        else:
            cursor.execute('''
                SELECT id, question_text, options, correct_answer, explanation, question_type
                FROM test_questions
            ''')
        
        questions = []
        for row in cursor.fetchall():
            questions.append({
                'id': row[0],
                'question_text': row[1],
                'options': json.loads(row[2]),
                'correct_answer': row[3],
                'explanation': row[4],
                'question_type': row[5]
            })
        
        conn.close()
        return questions
    
    def evaluate_test(self, answers):
        """Оценивает тест и возвращает результат"""
        questions = self.get_test_questions()
        total_questions = len(questions)
        correct_answers = 0
        
        for question in questions:
            question_id = str(question['id'])
            if question_id in answers and int(answers[question_id]) == question['correct_answer']:
                correct_answers += 1
        
        score = (correct_answers / total_questions) * 100
        passed = score >= 80  # 80% для прохождения
        
        return {
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'score': round(score, 1),
            'passed': passed,
            'answers_detail': self.get_answers_detail(questions, answers)
        }
    
    def get_answers_detail(self, questions, user_answers):
        """Возвращает детальную информацию по ответам"""
        detail = []
        for question in questions:
            question_id = str(question['id'])
            user_answer = int(user_answers.get(question_id, -1))
            is_correct = user_answer == question['correct_answer']
            
            detail.append({
                'question': question['question_text'],
                'user_answer': question['options'][user_answer] if user_answer != -1 else 'Не отвечено',
                'correct_answer': question['options'][question['correct_answer']],
                'is_correct': is_correct,
                'explanation': question['explanation']
            })
        
        return detail