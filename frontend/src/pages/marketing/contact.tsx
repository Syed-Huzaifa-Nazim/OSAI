import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { motion } from 'framer-motion'
import { CheckCircle2, Mail, MapPin, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { FormField } from '@/components/ui/form-field'
import { Section } from '@/components/marketing/section'
import { ContactVisual } from '@/components/marketing/contact-visual'
import { contactSchema, type ContactValues } from '@/lib/validation'
import { contactApi } from '@/lib/api/services'
import { errorMessage } from '@/lib/api-client'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { spring } from '@/lib/motion'

export default function ContactPage() {
  useDocumentTitle('Contact')
  const [sent, setSent] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ContactValues>({
    resolver: zodResolver(contactSchema),
    defaultValues: { name: '', email: '', organisation: '', message: '' },
  })

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      await contactApi.submit({
        name: values.name,
        email: values.email,
        organisation: values.organisation || null,
        message: values.message,
      })
      setSent(true)
      reset()
    } catch (error) {
      setFormError(errorMessage(error))
    }
  })

  return (
    <>
      <section className="pb-0 pt-10 sm:pt-14">
        <div className="container">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={spring}
            className="max-w-2xl"
          >
            <p className="eyebrow">Contact</p>
            <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight sm:text-5xl">
              Get in touch
            </h1>
            <p className="mt-5 text-lg leading-relaxed text-muted-foreground">
              Questions about the project, the research, or running it against your own competitor
              set. This reaches the team.
            </p>
          </motion.div>
        </div>
      </section>

      <Section className="pt-6 sm:pt-8">
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <Card className="p-7 sm:p-8">
            {sent ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={spring}
                className="flex flex-col items-center py-12 text-center"
              >
                <span className="flex size-12 items-center justify-center rounded-full bg-success/15 text-success">
                  <CheckCircle2 className="size-6" />
                </span>
                <h2 className="mt-5 font-display text-lg font-semibold">Message received</h2>
                <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                  Your message has been stored. Email delivery is not wired up yet, so someone on
                  the team will pick it up from the submissions table rather than an inbox.
                </p>
                <Button
                  variant="outline"
                  className="mt-6"
                  onClick={() => {
                    setSent(false)
                  }}
                >
                  Send another
                </Button>
              </motion.div>
            ) : (
              <form onSubmit={onSubmit} className="space-y-5" noValidate>
                {formError ? (
                  <p
                    role="alert"
                    className="rounded-md border border-destructive/25 bg-destructive/10 p-3 text-sm text-destructive"
                  >
                    {formError}
                  </p>
                ) : null}

                <div className="grid gap-5 sm:grid-cols-2">
                  <FormField label="Name" htmlFor="name" error={errors.name?.message} required>
                    <Input
                      id="name"
                      autoComplete="name"
                      aria-invalid={Boolean(errors.name)}
                      {...register('name')}
                    />
                  </FormField>
                  <FormField label="Email" htmlFor="email" error={errors.email?.message} required>
                    <Input
                      id="email"
                      type="email"
                      autoComplete="email"
                      aria-invalid={Boolean(errors.email)}
                      {...register('email')}
                    />
                  </FormField>
                </div>

                <FormField
                  label="Organisation"
                  htmlFor="organisation"
                  error={errors.organisation?.message}
                  hint="Optional"
                >
                  <Input
                    id="organisation"
                    autoComplete="organization"
                    {...register('organisation')}
                  />
                </FormField>

                <FormField
                  label="Message"
                  htmlFor="message"
                  error={errors.message?.message}
                  required
                >
                  <Textarea
                    id="message"
                    rows={6}
                    placeholder="What would you like to know?"
                    aria-invalid={Boolean(errors.message)}
                    {...register('message')}
                  />
                </FormField>

                <Button type="submit" loading={isSubmitting}>
                  {isSubmitting ? 'Sending…' : 'Send message'}
                  {isSubmitting ? null : <Send />}
                </Button>
              </form>
            )}
          </Card>

          <div className="space-y-4">
            <ContactVisual />
            <Card glass className="p-6">
              <span className="flex size-9 items-center justify-center rounded-full bg-primary/12 text-primary">
                <MapPin className="size-4" />
              </span>
              <h2 className="mt-4 font-display text-base font-semibold">Where we are</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                Department of Artificial Intelligence
                <br />
                Faculty of Information &amp; Computing Sciences
                <br />
                Dawood University of Engineering &amp; Technology
              </p>
            </Card>

            <Card glass className="p-6">
              <span className="flex size-9 items-center justify-center rounded-full bg-primary/12 text-primary">
                <Mail className="size-4" />
              </span>
              <h2 className="mt-4 font-display text-base font-semibold">On email delivery</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                Submissions are stored in the database, but outbound email is not configured yet.
                Wiring up a transactional provider is tracked in the project status log.
              </p>
            </Card>
          </div>
        </div>
      </Section>
    </>
  )
}
