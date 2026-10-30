# Stage I2 composition declaration

Stage I2 records intended cross-application interfaces. It does not connect
applications, grant a capability, execute an effect, or admit an application.

1. Start from the exact latest Stage I1 CAS object.
2. Preserve its application, index, THR, semantic-authority, effect-executor,
   identity, jurisdiction, and authority-ceiling fields.
3. Declare only interfaces supported by a named capability and exact schema
   root. Internal routes remain internal.
4. A provider lists intended consumers. Each consumer separately accepts or
   rejects each tuple. Provider invitation alone never creates an edge.
5. Keep optional intentions `required: false` until a later contract explicitly
   makes them required.
6. Import returned bytes through `portfolio-import-stage2`; do not normalize
   away the source artifact. Use `portfolio-campaign-preflight` to derive the
   current bilateral graph from journaled CAS objects.
7. Send rejections back to the provider and import its successor declaration.
8. A clean preflight advances only to a correspondence court. It never grants
   execution, custody, identity, jurisdiction, or authority.
