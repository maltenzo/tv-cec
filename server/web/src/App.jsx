import { useEffect, useState } from 'react';
import {
  ActionIcon, AppShell, Badge, Button, Card, Container, Group, Modal, PasswordInput, Progress, SimpleGrid,
  Stack, Switch, Text, TextInput, ThemeIcon, Title, Tooltip, useComputedColorScheme, useMantineColorScheme,
} from '@mantine/core';
import { Dropzone } from '@mantine/dropzone';
import { notifications } from '@mantine/notifications';
import { useInterval } from '@mantine/hooks';
import {
  IconArrowDown, IconArrowUp, IconDeviceTv, IconDeviceTvOff, IconMoon, IconMovie, IconPhoto, IconPlaylistAdd,
  IconPower, IconSun, IconTerminal2, IconTrash, IconUpload, IconX,
} from '@tabler/icons-react';

// extensiones explícitas: en Linux el navegador a veces no le pone tipo a los .mov
const ACCEPT = { 'video/*': ['.mp4', '.mkv', '.mov', '.webm', '.avi'], 'image/*': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'] };
const fail = e => notifications.show({ color: 'red', title: 'Error', message: e.message });
const ok = message => notifications.show({ color: 'teal', message });

export default function App() {
  const [token, setToken] = useState(() => { try { return localStorage.token || ''; } catch { return ''; } });
  const [state, setState] = useState({ media: {}, playlist: [], schedule: null });
  const [status, setStatus] = useState(undefined);
  const [uploads, setUploads] = useState({});  // nombre -> %
  const [toDelete, setToDelete] = useState(null);

  async function api(method, path, body) {
    const r = await fetch(path, { method, headers: { Authorization: 'Bearer ' + token }, body: body && JSON.stringify(body) });
    if (r.status === 401) { saveToken(''); throw Error('Token incorrecto'); }
    if (!r.ok) throw Error(await r.text());
    return r.json();
  }
  const run = fn => fn().catch(fail);
  const saveToken = t => { try { t ? (localStorage.token = t) : localStorage.removeItem('token'); } catch {} setToken(t); };
  const update = body => run(async () => setState(await api('PUT', '/state', body)));

  const refreshStatus = () => token && api('GET', '/status').then(setStatus, () => setStatus(null));
  useInterval(refreshStatus, 5000, { autoInvoke: true });
  useEffect(() => { if (token) { refreshStatus(); run(async () => setState(await api('GET', '/state'))); } }, [token]);

  const upload = file => new Promise((res, rej) => {  // XHR y no fetch: da progreso
    const x = new XMLHttpRequest();
    x.open('POST', '/media?name=' + encodeURIComponent(file.name));
    x.setRequestHeader('Authorization', 'Bearer ' + token);
    x.upload.onprogress = e => setUploads(u => ({ ...u, [file.name]: (100 * e.loaded) / e.total }));
    x.onload = () => (x.status < 300 ? res() : rej(Error(`${file.name}: ${x.responseText}`)));
    x.onerror = () => rej(Error(`${file.name}: error de red`));
    x.send(file);
  }).finally(() => setUploads(({ [file.name]: _, ...u }) => u));

  const onDrop = files => run(async () => {
    for (const f of files) await upload(f);
    setState(await api('GET', '/state'));
    ok(files.length > 1 ? `${files.length} archivos subidos` : `${files[0].name} subido`);
  });

  const command = (cmd, label) => run(async () => { await api('POST', '/command', { cmd }); ok(`${label}: la Pi lo hace en menos de 15 s`); });
  const move = (i, d) => { const p = [...state.playlist]; [p[i], p[i + d]] = [p[i + d], p[i]]; update({ playlist: p }); };
  const name = sha => state.media[sha]?.name ?? sha.slice(0, 8);

  return (
    <AppShell header={{ height: 60 }} padding="md">
      <AppShell.Header>
        <Container size="lg" h="100%">
          <Group h="100%" justify="space-between">
            <Group gap="xs"><ThemeIcon variant="light" size="lg"><IconDeviceTv size={20} /></ThemeIcon><Title order={3}>Tele</Title></Group>
            <Group gap="xs"><StatusBadge status={status} /><SchemeToggle /></Group>
          </Group>
        </Container>
      </AppShell.Header>

      <AppShell.Main>
        <Container size="lg">
          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
            <Stack gap="md">
              <Section title="Control" subtitle="La Pi ejecuta la orden en menos de 15 s.">
                <StatusDetail status={status} />
                <Group mt="md" grow>
                  <Button leftSection={<IconPower size={18} />} onClick={() => command('on', 'Prender')}>Prender</Button>
                  <Button variant="default" leftSection={<IconDeviceTvOff size={18} />} onClick={() => command('off', 'Apagar')}>Apagar</Button>
                </Group>
                <Button mt="xs" fullWidth variant="subtle" color="gray" leftSection={<IconTerminal2 size={18} />} onClick={() => command('console', 'Video / consola')}>
                  Alternar video / consola
                </Button>
              </Section>
              <Schedule schedule={state.schedule} onSave={schedule => run(async () => { setState(await api('PUT', '/state', { schedule })); ok('Horario guardado'); })} />
            </Stack>

            <Section title="Playlist" subtitle="Se repite en loop, en este orden.">
              {state.playlist.length ? (
                <Stack gap={4}>
                  {state.playlist.map((sha, i) => (
                    <Row key={i + sha} icon={<Text c="dimmed" fw={600} w={20} ta="center">{i + 1}</Text>} label={name(sha)} kind={state.media[sha]?.kind}>
                      <Tooltip label="Subir"><ActionIcon variant="subtle" color="gray" disabled={!i} onClick={() => move(i, -1)}><IconArrowUp size={16} /></ActionIcon></Tooltip>
                      <Tooltip label="Bajar"><ActionIcon variant="subtle" color="gray" disabled={i === state.playlist.length - 1} onClick={() => move(i, 1)}><IconArrowDown size={16} /></ActionIcon></Tooltip>
                      <Tooltip label="Quitar de la playlist"><ActionIcon variant="subtle" color="red" onClick={() => update({ playlist: state.playlist.filter((_, j) => j !== i) })}><IconX size={16} /></ActionIcon></Tooltip>
                    </Row>
                  ))}
                </Stack>
              ) : <Empty>Vacía: agregá algo de la biblioteca.</Empty>}
            </Section>
          </SimpleGrid>

          <Section mt="md" title="Biblioteca" subtitle="Videos e imágenes subidos. Agregalos a la playlist para que se vean.">
            <Dropzone onDrop={onDrop} onReject={() => fail(Error('Formato no soportado'))} accept={ACCEPT} loading={Object.keys(uploads).length > 0}>
              <Group justify="center" gap="md" mih={90} style={{ pointerEvents: 'none' }}>
                <IconUpload size={36} stroke={1.5} color="var(--mantine-color-dimmed)" />
                <div>
                  <Text fw={500}>Arrastrá archivos o hacé clic para elegir</Text>
                  <Text size="sm" c="dimmed">Videos (mp4, mov, mkv, webm, avi) o imágenes</Text>
                </div>
              </Group>
            </Dropzone>
            {Object.entries(uploads).map(([n, p]) => (
              <div key={n}><Text size="sm" mt="sm">{n}</Text><Progress value={p} animated /></div>
            ))}
            <Stack gap={4} mt="md">
              {Object.entries(state.media).map(([sha, m]) => (
                <Row key={sha} icon={<KindIcon kind={m.kind} />} label={m.name} kind={m.kind}>
                  <Button visibleFrom="sm" size="xs" variant="light" leftSection={<IconPlaylistAdd size={16} />} onClick={() => update({ playlist: [...state.playlist, sha] })}>Agregar</Button>
                  <Tooltip label="Agregar a la playlist"><ActionIcon hiddenFrom="sm" variant="light" onClick={() => update({ playlist: [...state.playlist, sha] })}><IconPlaylistAdd size={16} /></ActionIcon></Tooltip>
                  <Tooltip label="Borrar"><ActionIcon variant="subtle" color="red" onClick={() => setToDelete(sha)}><IconTrash size={16} /></ActionIcon></Tooltip>
                </Row>
              ))}
              {!Object.keys(state.media).length && <Empty>Nada subido todavía.</Empty>}
            </Stack>
          </Section>
        </Container>
      </AppShell.Main>

      <Modal opened={!!toDelete} onClose={() => setToDelete(null)} title="Borrar archivo" centered>
        <Text>¿Borrar <b>{toDelete && name(toDelete)}</b>? También se quita de la playlist.</Text>
        <Group justify="flex-end" mt="lg">
          <Button variant="default" onClick={() => setToDelete(null)}>Cancelar</Button>
          <Button color="red" onClick={() => { const sha = toDelete; setToDelete(null); run(async () => setState(await api('DELETE', '/media/' + sha))); }}>Borrar</Button>
        </Group>
      </Modal>

      <TokenModal opened={!token} onSave={saveToken} />
    </AppShell>
  );
}

function Section({ title, subtitle, children, ...props }) {
  return (
    <Card withBorder padding="lg" {...props}>
      <Title order={4}>{title}</Title>
      {subtitle && <Text size="sm" c="dimmed" mb="md">{subtitle}</Text>}
      {children}
    </Card>
  );
}

function Row({ icon, label, kind, children }) {
  return (
    <Group wrap="nowrap" gap="sm" py={6} px="xs" style={{ borderRadius: 'var(--mantine-radius-sm)', background: 'var(--mantine-color-default-hover)' }}>
      {icon}
      <Text flex={1} miw={0} truncate="end" title={label}>{label}</Text>
      {kind && <Badge visibleFrom="sm" variant="light" color={kind === 'video' ? 'indigo' : 'grape'} size="sm">{kind === 'video' ? 'video' : 'imagen'}</Badge>}
      <Group gap={4} wrap="nowrap">{children}</Group>
    </Group>
  );
}

const KindIcon = ({ kind }) => (
  <ThemeIcon variant="light" color={kind === 'video' ? 'indigo' : 'grape'} size="md">{kind === 'video' ? <IconMovie size={16} /> : <IconPhoto size={16} />}</ThemeIcon>
);
const Empty = ({ children }) => <Text c="dimmed" size="sm" ta="center" py="lg">{children}</Text>;

function summary(st) {  // undefined: cargando · null: nunca reportó / sin API
  if (st === undefined) return { color: 'gray', text: 'Conectando…' };
  if (st === null) return { color: 'gray', text: 'Sin datos de la Pi' };
  if (st.age > 60) return { color: 'red', text: 'Pi sin conexión' };
  return st.tv === 'on' ? { color: 'teal', text: 'Tele prendida' } : st.tv === 'standby' ? { color: 'yellow', text: 'Tele apagada' } : { color: 'gray', text: 'Tele sin datos' };
}

const StatusBadge = ({ status }) => {
  const s = summary(status);
  return <Badge variant="dot" color={s.color} size="lg">{s.text}</Badge>;
};

function StatusDetail({ status }) {
  const s = summary(status);
  const fresh = status && status.age <= 60;
  return (
    <SimpleGrid cols={3} spacing="xs">
      <Stat label="Tele" value={fresh ? { on: 'Prendida', standby: 'Apagada' }[status.tv] ?? 'Sin datos' : '—'} color={s.color} />
      <Stat label="Pantalla" value={fresh ? (status.video ? 'Video' : 'Consola') : '—'} />
      <Stat label="Último aviso" value={status ? (status.age < 90 ? `hace ${Math.round(status.age)} s` : `hace ${Math.round(status.age / 60)} min`) : '—'} />
    </SimpleGrid>
  );
}

const Stat = ({ label, value, color }) => (
  <Card padding="sm" bg="var(--mantine-color-default-hover)">
    <Text size="xs" c="dimmed" tt="uppercase" fw={600}>{label}</Text>
    <Text fw={600} c={color && color !== 'gray' ? `${color}.6` : undefined}>{value}</Text>
  </Card>
);

function Schedule({ schedule, onSave }) {
  const [on, setOn] = useState(!!schedule);
  const [times, setTimes] = useState({ on: '08:00', off: '22:00' });
  useEffect(() => { setOn(!!schedule); if (schedule) setTimes(schedule); }, [schedule]);
  return (
    <Section title="Horario" subtitle="Prende y apaga la tele sola, con la hora local de la Pi.">
      <Switch label="Prender y apagar automáticamente" checked={on} onChange={e => setOn(e.currentTarget.checked)} />
      <Group grow mt="md">
        <TextInput type="time" label="Prende" disabled={!on} value={times.on} onChange={e => setTimes({ ...times, on: e.currentTarget.value })} />
        <TextInput type="time" label="Apaga" disabled={!on} value={times.off} onChange={e => setTimes({ ...times, off: e.currentTarget.value })} />
      </Group>
      <Group justify="flex-end" mt="md"><Button onClick={() => onSave(on ? times : null)}>Guardar horario</Button></Group>
    </Section>
  );
}

function SchemeToggle() {
  const { setColorScheme } = useMantineColorScheme();
  const dark = useComputedColorScheme('light') === 'dark';
  return (
    <Tooltip label={dark ? 'Modo claro' : 'Modo oscuro'}>
      <ActionIcon variant="default" size="lg" onClick={() => setColorScheme(dark ? 'light' : 'dark')}>{dark ? <IconSun size={18} /> : <IconMoon size={18} />}</ActionIcon>
    </Tooltip>
  );
}

function TokenModal({ opened, onSave }) {
  const [value, setValue] = useState('');
  return (
    <Modal opened={opened} onClose={() => {}} withCloseButton={false} centered title="Ingresar">
      <form onSubmit={e => { e.preventDefault(); value && onSave(value.trim()); }}>
        <PasswordInput label="Token de la API" description="Se guarda en este navegador." value={value} onChange={e => setValue(e.currentTarget.value)} data-autofocus />
        <Button type="submit" fullWidth mt="md">Entrar</Button>
      </form>
    </Modal>
  );
}
