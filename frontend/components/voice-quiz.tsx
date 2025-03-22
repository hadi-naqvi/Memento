"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Mic, MicOff, Volume2, CheckCircle, XCircle } from "lucide-react"
import { Progress } from "@/components/ui/progress"
import confetti from "canvas-confetti"

type QuizQuestion = {
  id: number
  question: string
  correctAnswer: string
}

const sampleQuestions: QuizQuestion[] = [
  {
    id: 1,
    question: "What day of the week is it today?",
    correctAnswer: "monday", // This would be dynamic in a real app
  },
  {
    id: 2,
    question: "What season are we currently in?",
    correctAnswer: "spring", // This would be dynamic in a real app
  },
  {
    id: 3,
    question: "What did you have for breakfast this morning?",
    correctAnswer: "", // Open-ended question, any answer is fine
  },
  {
    id: 4,
    question: "Can you name three types of fruits?",
    correctAnswer: "", // Open-ended question, any answer with fruits is fine
  },
  {
    id: 5,
    question: "What is your favorite hobby?",
    correctAnswer: "", // Open-ended question, any answer is fine
  },
]

// Declare SpeechRecognition interface
declare global {
  interface Window {
    SpeechRecognition: any
    webkitSpeechRecognition: any
    SpeechSynthesisUtterance: any
  }
}

export function VoiceQuiz() {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState("")
  const [feedback, setFeedback] = useState<string | null>(null)
  const [feedbackType, setFeedbackType] = useState<"correct" | "incorrect" | null>(null)
  const [isComplete, setIsComplete] = useState(false)
  const [score, setScore] = useState(0)
  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const synthRef = useRef<SpeechSynthesis | null>(null)

  const currentQuestion = sampleQuestions[currentQuestionIndex]
  const progress = (currentQuestionIndex / sampleQuestions.length) * 100

  useEffect(() => {
    if (typeof window !== "undefined") {
      // Initialize speech recognition
      if ("SpeechRecognition" in window || "webkitSpeechRecognition" in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
        recognitionRef.current = new SpeechRecognition()
        recognitionRef.current.continuous = true
        recognitionRef.current.interimResults = true

        recognitionRef.current.onresult = (event) => {
          const transcript = Array.from(event.results)
            .map((result) => result[0])
            .map((result) => result.transcript)
            .join("")

          setTranscript(transcript)
        }

        recognitionRef.current.onend = () => {
          if (isListening) {
            recognitionRef.current?.start()
          }
        }
      }

      // Initialize speech synthesis
      if ("speechSynthesis" in window) {
        synthRef.current = window.speechSynthesis

        // Speak the first question when component mounts
        speakQuestion(sampleQuestions[0].question)
      }
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
      if (synthRef.current) {
        synthRef.current.cancel()
      }
    }
  }, [])

  const speakQuestion = (text: string) => {
    if (synthRef.current) {
      synthRef.current.cancel() // Cancel any ongoing speech
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.rate = 0.9 // Slightly slower rate for clarity
      synthRef.current.speak(utterance)
    }
  }

  const toggleListening = () => {
    if (isListening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
      if (transcript) {
        evaluateAnswer(transcript)
      }
    } else {
      if (recognitionRef.current) {
        recognitionRef.current.start()
      }
    }
    setIsListening(!isListening)
  }

  const evaluateAnswer = (answer: string) => {
    // For open-ended questions, any answer is acceptable
    if (currentQuestion.correctAnswer === "") {
      setFeedback("Thank you for your answer!")
      setFeedbackType("correct")
      setScore(score + 1)
      setTimeout(moveToNextQuestion, 2000)
      return
    }

    // For questions with specific answers, check if the answer contains the correct answer
    const normalizedAnswer = answer.toLowerCase()
    const normalizedCorrectAnswer = currentQuestion.correctAnswer.toLowerCase()

    if (normalizedAnswer.includes(normalizedCorrectAnswer)) {
      setFeedback("Correct! Well done.")
      setFeedbackType("correct")
      setScore(score + 1)
    } else {
      setFeedback(`The correct answer was: ${currentQuestion.correctAnswer}`)
      setFeedbackType("incorrect")
    }

    setTimeout(moveToNextQuestion, 3000)
  }

  const moveToNextQuestion = () => {
    setTranscript("")
    setFeedback(null)
    setFeedbackType(null)

    if (currentQuestionIndex < sampleQuestions.length - 1) {
      const nextIndex = currentQuestionIndex + 1
      setCurrentQuestionIndex(nextIndex)
      speakQuestion(sampleQuestions[nextIndex].question)
    } else {
      setIsComplete(true)

      // Trigger confetti if score is good
      if (score / sampleQuestions.length >= 0.6 && typeof window !== "undefined") {
        setTimeout(() => {
          confetti({
            particleCount: 100,
            spread: 70,
            origin: { y: 0.6 },
          })
        }, 500)
      }
    }
  }

  const restartQuiz = () => {
    setCurrentQuestionIndex(0)
    setTranscript("")
    setFeedback(null)
    setFeedbackType(null)
    setIsComplete(false)
    setScore(0)
    speakQuestion(sampleQuestions[0].question)
  }

  const repeatQuestion = () => {
    speakQuestion(currentQuestion.question)
  }

  if (isComplete) {
    return (
      <Card className="border-0 shadow-lg overflow-hidden">
        <CardHeader className="gradient-bg text-white text-center">
          <CardTitle className="text-2xl">Quiz Complete!</CardTitle>
        </CardHeader>
        <CardContent className="text-center space-y-6 p-8">
          <div className="w-24 h-24 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
            <span className="text-4xl font-bold text-primary">
              {score}/{sampleQuestions.length}
            </span>
          </div>

          <div>
            <h3 className="text-xl font-medium mb-2">Great job!</h3>
            <p className="text-muted-foreground">You've completed today's memory quiz.</p>
          </div>

          <div className="flex justify-center gap-4">
            <Button variant="outline" onClick={restartQuiz} className="px-6">
              Try Again
            </Button>
            <Button onClick={() => (window.location.href = "/dashboard")} className="px-6">
              Back to Home
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-0 shadow-lg overflow-hidden">
      <CardHeader className="gradient-bg text-white">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium">
            Question {currentQuestionIndex + 1} of {sampleQuestions.length}
          </span>
          <span className="text-sm font-medium">{Math.round(progress)}%</span>
        </div>
        <Progress value={progress} className="h-2 mt-2 bg-white/20" />
      </CardHeader>
      <CardContent className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-medium">{currentQuestion.question}</h2>
          <Button variant="ghost" size="icon" onClick={repeatQuestion} title="Repeat question" className="h-8 w-8">
            <Volume2 className="h-5 w-5" />
            <span className="sr-only">Repeat question</span>
          </Button>
        </div>

        {transcript && (
          <div className="p-4 bg-muted rounded-lg">
            <p className="font-medium">Your answer:</p>
            <p>{transcript}</p>
          </div>
        )}

        {feedback && (
          <div
            className={`p-4 rounded-lg flex items-start gap-3 ${
              feedbackType === "correct"
                ? "bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-300"
                : "bg-amber-50 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300"
            }`}
          >
            {feedbackType === "correct" ? (
              <CheckCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
            ) : (
              <XCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
            )}
            <p>{feedback}</p>
          </div>
        )}
      </CardContent>
      <CardFooter className="flex justify-center p-6 pt-0">
        <Button
          size="lg"
          className={`rounded-full h-16 w-16 p-0 ${isListening ? "recording-animation bg-red-500 hover:bg-red-600" : "speak-button"}`}
          onClick={toggleListening}
        >
          {isListening ? <MicOff className="h-6 w-6 text-white" /> : <Mic className="h-6 w-6 text-white" />}
          <span className="sr-only">{isListening ? "Stop" : "Answer"}</span>
        </Button>
      </CardFooter>
    </Card>
  )
}

