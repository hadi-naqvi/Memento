import Image from "next/image"
import { Card, CardContent } from "@/components/ui/card"
import { Clock } from "lucide-react"

interface ReminderCardProps {
  title: string
  description: string
  imageSrc: string
  time: string
}

export function ReminderCard({ title, description, imageSrc, time }: ReminderCardProps) {
  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow border border-border/50">
      <CardContent className="p-0">
        <div className="flex items-start p-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium text-primary">{time}</span>
            </div>
            <h3 className="text-lg font-semibold">{title}</h3>
            <p className="text-muted-foreground text-sm mt-1">{description}</p>
          </div>
          <div className="ml-4 rounded-md overflow-hidden">
            <Image
              src={imageSrc || "/placeholder.svg"}
              alt="Reminder illustration"
              width={100}
              height={100}
              className="object-cover rounded-md"
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

