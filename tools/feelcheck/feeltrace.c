/*
 * TrueCombat: Platinum feel check (tools/feelcheck). feeltrace.py puts this code into feel-check
 * builds only, never into a release. With sv_feelTrace <file> the server runs every frame as exactly
 * 8 ms of game time (so the simulation no longer depends on the real clock) and writes, after each
 * game frame, the state of every active client and a hash of all linked entities. Two builds that
 * play identically write identical files. sv_feelTraceFrames N quits after N traced frames.
 */
static cvar_t      *sv_feelTrace, *sv_feelTraceFrames;
static fileHandle_t feelTraceFile;
static int          feelTraceFrames;

static uint64_t SV_FeelHash(uint64_t h, const void *data, size_t len)
{
	const unsigned char *p = (const unsigned char *)data;
	size_t              i;

	for (i = 0; i < len; i++)
	{
		h ^= p[i];
		h *= 1099511628211ULL;
	}
	return h;
}

static void SV_FeelTraceFrame(void)
{
	char     line[1024];
	uint64_t world = 14695981039346656037ULL;
	int      i;

	if (!sv_feelTrace || !sv_feelTrace->string[0] || sv.state != SS_GAME)
	{
		return;
	}
	if (!feelTraceFile)
	{
		feelTraceFile = FS_FOpenFileWrite(sv_feelTrace->string);
		if (!feelTraceFile)
		{
			Com_Printf("feel trace: cannot open %s\n", sv_feelTrace->string);
			Cvar_Set("sv_feelTrace", "");
			return;
		}
		Com_sprintf(line, sizeof(line), "FEELTRACE 1 %s\n", sv_mapname->string);
		FS_Write(line, strlen(line), feelTraceFile);
	}
	for (i = 0; i < sv.num_entities; i++)
	{
		sharedEntity_t *ent = SV_GentityNum(i);

		if (ent->r.linked)
		{
			world = SV_FeelHash(world, &i, sizeof(i));
			world = SV_FeelHash(world, &ent->s, sizeof(ent->s));
		}
	}
	Com_sprintf(line, sizeof(line), "F %d %016llx\n", sv.time, (unsigned long long)world);
	FS_Write(line, strlen(line), feelTraceFile);
	for (i = 0; i < sv_maxclients->integer; i++)
	{
		playerState_t ps;

		if (svs.clients[i].state != CS_ACTIVE)
		{
			continue;
		}
		ps      = *SV_GameClientNum(i);
		ps.ping = 0;    // the only field that follows the real network
		Com_sprintf(line, sizeof(line),
		            "P %d %016llx t=%d pm=%d pf=%d ef=%d o=%a,%a,%a v=%a,%a,%a a=%a,%a,%a w=%d ws=%d hp=%d clip=%d ammo=%d ev=%d\n",
		            i, (unsigned long long)SV_FeelHash(14695981039346656037ULL, &ps, sizeof(ps)), ps.commandTime, ps.pm_type,
		            (int)ps.pm_flags, (int)ps.eFlags, ps.origin[0], ps.origin[1], ps.origin[2], ps.velocity[0], ps.velocity[1],
		            ps.velocity[2], ps.viewangles[0], ps.viewangles[1], ps.viewangles[2], (int)ps.weapon, (int)ps.weaponstate,
		            (int)(short)ps.stats[STAT_HEALTH], (int)ps.ammoclip[ps.weapon % MAX_WEAPONS], (int)ps.ammo[ps.weapon % MAX_WEAPONS],
		            (int)ps.eventSequence);
		FS_Write(line, strlen(line), feelTraceFile);
	}
	if (sv_feelTraceFrames->integer > 0 && ++feelTraceFrames >= sv_feelTraceFrames->integer)
	{
		FS_FCloseFile(feelTraceFile);
		feelTraceFile = 0;
		Cvar_Set("sv_feelTrace", "");
		Com_Printf("feel trace: %d frames written\n", feelTraceFrames);
		Cbuf_AddText("quit\n");
	}
}

/* Called at the top of SV_Frame: registers the cvars and, while tracing, fixes the frame to 8 ms of game time. */
static int SV_FeelTraceMsec(int msec)
{
	if (!sv_feelTrace)
	{
		sv_feelTrace       = Cvar_Get("sv_feelTrace", "", CVAR_INIT);
		sv_feelTraceFrames = Cvar_Get("sv_feelTraceFrames", "0", CVAR_INIT);
	}
	return sv_feelTrace->string[0] ? 8 : msec;
}

