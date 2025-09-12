FROM alpine:3

# Install dependencies
RUN apk add --update --no-cache curl

# Copy update script
COPY update-dns.sh /usr/local/bin/update-dns.sh
RUN chmod +x /usr/local/bin/update-dns.sh

# Default command
CMD ["/usr/local/bin/update-dns.sh"]
