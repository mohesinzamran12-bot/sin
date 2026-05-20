import { MapPin, Building2, ExternalLink } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate, formatSalary } from "@/lib/utils";
import type { Job } from "@/types";

interface JobCardProps {
  job: Job;
  onClick?: () => void;
}

export function JobCard({ job, onClick }: JobCardProps) {
  return (
    <Card
      className="cursor-pointer hover:shadow-md transition-shadow"
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">{job.title}</CardTitle>
          <Badge variant={job.source === "manual" ? "secondary" : "default"}>
            {job.source}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Building2 className="h-3.5 w-3.5" />
          <span>{job.company_name}</span>
        </div>

        {job.city && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <MapPin className="h-3.5 w-3.5" />
            <span>{job.city}</span>
          </div>
        )}

        <div className="flex items-center justify-between pt-1">
          <span className="text-sm font-medium text-foreground">
            {formatSalary(job.salary_min, job.salary_max, job.salary_range)}
          </span>
          <span className="text-xs text-muted-foreground">
            {formatDate(job.created_at)}
          </span>
        </div>

        {!job.is_active && (
          <Badge variant="destructive" className="text-xs">
            Inactive
          </Badge>
        )}

        {job.url && (
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-primary hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink className="h-3 w-3" />
            View posting
          </a>
        )}
      </CardContent>
    </Card>
  );
}
