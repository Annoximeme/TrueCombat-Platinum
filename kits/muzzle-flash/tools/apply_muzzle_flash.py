#!/usr/bin/env python3
"""Muzzle flash pass (0.39.1): applies the change to a source tree (0.39.0, or 0.40 with particles 05+14).
usage: apply_muzzle_flash.py <source root>   (CRLF kept)"""
import sys,re
root=sys.argv[1].rstrip('/')+'/game_src/native/'
def load(f):
    b=open(root+f,'rb').read().decode('latin1');return b.replace('\r\n','\n')
def save(f,s):open(root+f,'wb').write(s.replace('\n','\r\n').encode('latin1'))
def rep(s,a,b,regex=False):
    if regex:
        n=len(re.findall(a,s));assert n==1,(a[:70],n);return re.sub(a,lambda m:b.replace('\\1',m.group(1) if m.groups() else ''),s)
    assert s.count(a)==1,(a[:70],s.count(a));return s.replace(a,b)

# ---------------- tcp_weapon_media.h ----------------
f='tcp_weapon_media.h';s=load(f)
s=rep(s,'static wmMedia_t wmMedia[WM_MAX_WEAPONS];\n','static wmMedia_t wmMedia[WM_MAX_WEAPONS];\nstatic vmCvar_t pmFlashHold; /* cg_muzzleFlashHold (cheat): 1 keeps every muzzle flash drawn, 2 also brighter (placement checks, shots) */\n')
a='    if(wmValue(text,end,"handsModel",value,sizeof(value),NULL))m->hands=wmModel(value);\n'
s=rep(s,a,a+'''    /* 0.39.1: the stock Akimbo Glock/Beretta now draw both guns on the akimbo hands like the CQB Akimbo M1911, so
     * they take its view geometry (their own 2.5 0 5 / foreShorten 0.5 framed the guns at the screen corners). */
    if((weapon==37||weapon==38)&&m->hands){m->offset[0]=11.5f;m->offset[1]=0;m->offset[2]=5;m->aimOffset[0]=-4;m->aimOffset[1]=4.97f;m->aimOffset[2]=-3.7f;m->foreShorten=.75f;}
''')
s=rep(s,'/* Muzzle flash colour.','''/* Muzzle flash direction: the flash leaves along the bore. TC:E's own guns carry tag_flash along the
 * model's x axis (the bore), but some later models point it elsewhere: the CQB pack M4, M16 and G3A3 turn it
 * 180 degrees (the flash fired back into the gun) and the TC:E pistol world models tilt it 11 degrees down.
 * When the tag is more than 3 degrees off the parent's x axis, the flash takes the parent's axes; the tag
 * still gives the position. Scale (foreshortened view axes) is kept. */
static void wmFlashBore(refEntity_t *flash,const refEntity_t *parent){
    const float *f=flash->axis[0],*x=parent->axis[0];
    const float lf=sqrtf(f[0]*f[0]+f[1]*f[1]+f[2]*f[2]),lx=sqrtf(x[0]*x[0]+x[1]*x[1]+x[2]*x[2]);
    if(lf<=0||lx<=0||(f[0]*x[0]+f[1]*x[1]+f[2]*x[2])/(lf*lx)>.9986f)return; /* cos 3 degrees */
    memcpy(flash->axis,parent->axis,sizeof(flash->axis));
}
/* Muzzle flash position along the bore: a tag_flash set back inside the barrel or flash hider (CQB pack M4 1.9
 * units, M16 2.3, G3A3 1.1; world M4, M16, M76, R93 0.6 to 1.4) hides the base of the flash in the gun. The
 * front of the model (its frame 0 bounds) is the muzzle, so a tag up to 6 units behind it moves forward to it. */
static void wmFlashMuzzle(refEntity_t *flash,const refEntity_t *parent){
    if(!parent->hModel)return;
    vec3_t mins,maxs;SystemCall(CG_R_MODELBOUNDS,parent->hModel,mins,maxs);
    const float *x=parent->axis[0],l2=x[0]*x[0]+x[1]*x[1]+x[2]*x[2];if(l2<=0)return;
    vec3_t d;VectorSubtract(flash->origin,parent->origin,d);
    const float at=(d[0]*x[0]+d[1]*x[1]+d[2]*x[2])/l2,gap=maxs[0]-at;
    if(gap>.25f&&gap<6.f){VectorMA(flash->origin,gap,x,flash->origin);VectorCopy(flash->origin,flash->oldorigin);}
}
/* Muzzle flash colour.''')
s=rep(s,'    for(int i=0;i<passes;i++)SystemCall(CG_R_ADDREFENTITYTOSCENE,flash);',
'''    const int extra=pmFlashHold.integer>=2?4:0; /* cg_muzzleFlashHold 2: brighter, for placement checks */
    for(int i=0;i<passes+extra;i++)SystemCall(CG_R_ADDREFENTITYTOSCENE,flash);''')
save(f,s)

# ---------------- tcp_player_models.h ----------------
f='tcp_player_models.h';s=load(f)
a='    SystemCall(CG_CVAR_REGISTER,&pmThirdPerson,"cg_thirdPerson","0",CVAR_CHEAT);\n'
s=rep(s,a,a+'    SystemCall(CG_CVAR_REGISTER,&pmFlashHold,"cg_muzzleFlashHold","0",CVAR_CHEAT); /* muzzle flash check: keep every flash on screen */\n')
s=rep(s,'if(firing&&flashModel&&in->weapon!=TCP_SMOKE_WEAPON){','if((firing||pmFlashHold.integer)&&flashModel&&in->weapon!=TCP_SMOKE_WEAPON){')
# third person: firing gun, bore axis, muzzle; keep anything appended after wmAddFlash(&flash); (0.40 fxMuzzle)
s=rep(s,r'            VectorCopy\(origin,flash.lightingOrigin\);pmOnTag\(&flash,&part,"tag_flash",0\);wmFlashRoll\(&flash\);wmAddFlash\(&flash\);([^\n]*)\n',
'''            /* 0.39.1 akimbo: odd shots fire the left pistol (firing_akimbo2), so the flash goes to its muzzle. */
            refEntity_t gun=part;if(set==PM_SET_AKIMBO&&(in->shots&1))pmOnTag(&gun,&body,"tag_weapon2",0);
            VectorCopy(origin,flash.lightingOrigin);pmOnTag(&flash,&gun,"tag_flash",0);wmFlashBore(&flash,&gun);wmFlashMuzzle(&flash,&gun);wmFlashRoll(&flash);wmAddFlash(&flash);\\1
            if(pmFlashHold.integer&&set==PM_SET_AKIMBO&&!(in->shots&1)){refEntity_t l=part,f2=flash;pmOnTag(&l,&body,"tag_weapon2",0);pmOnTag(&f2,&l,"tag_flash",0);wmFlashBore(&f2,&l);wmFlashMuzzle(&f2,&l);wmAddFlash(&f2);}
''',regex=True)
s=rep(s,'/* View muzzle flash timing,','''/* 0.39.1: muzzle (barrel tip, bore centre) of each first-person akimbo gun in its sleeve model's frame, measured
 * from the meshes (right and left sleeve models share it within 0.4 units). */
static const float *pmAkimboMuzzle(int weapon){
    static const float beretta[3]={39.4f,-4.0f,-2.65f},glock[3]={38.9f,-4.05f,-3.25f},colt[3]={38.4f,-4.3f,-2.95f},shorty[3]={49.9f,-4.4f,-2.5f};
    switch(weapon){case 38:return beretta;case 37:return glock;case 58:return colt;case 61:return shorty;default:return NULL;}
}
/* View muzzle flash timing,''')
s=rep(s,'    const int cqbHands=m->hands&&m->parts&&TCP_GearExt(weapon)&&TCP_WeaponAkimbo(weapon); /* 0.38.0 */',
'''    /* 0.38.0 CQB akimbo; 0.39.1 also the stock Akimbo Beretta/Glock (same layout), which showed only the right gun
     * and no muzzle flash in first person. */
    const int cqbHands=m->hands&&m->parts&&TCP_WeaponAkimbo(weapon)&&weapon!=53&&weapon!=54;
    refEntity_t akGun[2];memset(akGun,0,sizeof(akGun)); /* akimbo: [0] right gun (tag_weapon), [1] left gun (tag_barrel3) */''')
s=rep(s,'pmOnTag(&gun,&hand,"tag_weapon",0);SystemCall(CG_R_ADDREFENTITYTOSCENE,&gun);\n','pmOnTag(&gun,&hand,"tag_weapon",0);SystemCall(CG_R_ADDREFENTITYTOSCENE,&gun);akGun[0]=gun;\n')
s=rep(s,'''        if(i==0)main=part;\n''','''        if(i==0)main=part;\n        if(cqbHands&&!strcmp(m->partTag[i],"tag_barrel3"))akGun[1]=part;\n''')
s=rep(s,'((pmFlashTime.shots+pmFlashTime.credit)&1)?"tag_brass2":"tag_brass",0);','((pmFlashTime.shots+pmFlashTime.credit)&1)?"tag_brass":"tag_brass2",0); /* 0.39.1: even shots = ATTACK1 = right gun (tag_brass2) */')
s=rep(s,'    if(m->viewFlash&&time-pmFlashTime.fired<30){','    if(m->viewFlash&&(time-pmFlashTime.fired<30||pmFlashHold.integer)){')
s=rep(s,'''        refEntity_t base=hand;const char *tag="tag_flash";
        if(TCP_WeaponAkimbo(weapon)&&weapon!=53&&weapon!=54){if((pmFlashTime.shots+pmFlashTime.credit)&1)tag="tag_flash2";}''',
'''        refEntity_t base=hand;const char *tag="tag_flash";
        const int side=(pmFlashTime.shots+pmFlashTime.credit)&1; /* akimbo: ATTACK1 (even) kicks the right gun, ATTACK2 the left */
        const float *mz=pmAkimboMuzzle(weapon);
        if(cqbHands&&mz&&akGun[side].hModel){
            /* 0.39.1: the hands' tag_flash/tag_flash2 sit at ET's Colt muzzles on the opposite gun; the flash goes to
             * the muzzle of the gun that fired (its model's barrel tip, both guns share the layout). */
            const refEntity_t *g=&akGun[side];VectorCopy(g->origin,flash.origin);
            for(int k=0;k<3;k++)VectorMA(flash.origin,mz[k],g->axis[k],flash.origin);
            VectorCopy(flash.origin,flash.oldorigin);memcpy(flash.axis,g->axis,sizeof(flash.axis));
            if(pmFlashHold.integer){refEntity_t f2=flash;const refEntity_t *o=&akGun[!side];if(o->hModel){VectorCopy(o->origin,f2.origin);for(int k=0;k<3;k++)VectorMA(f2.origin,mz[k],o->axis[k],f2.origin);
                memcpy(f2.axis,o->axis,sizeof(f2.axis));wmFlashRoll(&f2);wmAddFlash(&f2);}}
            wmFlashRoll(&flash);wmAddFlash(&flash);AKIMBO_FX
            {vec3_t at;VectorMA(rd->vieworg,24,rd->viewaxis[0],at);wmFlashLight(weapon,at);}
            return;
        }
        if(TCP_WeaponAkimbo(weapon)&&weapon!=53&&weapon!=54){if(side)tag="tag_flash2";}''')
m=re.search(r'        pmOnTag\(&flash,&base,tag,0\);wmFlashRoll\(&flash\);wmAddFlash\(&flash\);([^\n]*)\n',s);extra=m.group(1)
s=s.replace('AKIMBO_FX',extra)
s=rep(s,'''        else if(m->tagsInMain&&main.hModel){memset(&base,0,sizeof(base));base.reType=RT_MODEL;base.hModel=main.hModel;VectorCopy(main.origin,base.origin);memcpy(base.axis,main.axis,sizeof(base.axis));}
        pmOnTag(&flash,&base,tag,0);wmFlashRoll(&flash);wmAddFlash(&flash);'''+extra+'\n',
'''        else if(main.hModel){
            /* tagsInMain, or a gun whose main part carries its own tag_flash: the shotguns' hands keep
             * tag_flash at the M3's muzzle, so the M590 Compact flash floated 7 units ahead of its barrel
             * and the SPAS-12 flash started 4 units inside it. */
            refEntity_t p0;memset(&p0,0,sizeof(p0));p0.reType=RT_MODEL;p0.hModel=main.hModel;VectorCopy(main.origin,p0.origin);memcpy(p0.axis,main.axis,sizeof(p0.axis));
            orientation_t o;if(m->tagsInMain||SystemCall(CG_R_LERPTAG,&o,&p0,"tag_flash",0)>=0)base=p0;}
        pmOnTag(&flash,&base,tag,0);if(main.hModel&&base.hModel==main.hModel){wmFlashBore(&flash,&base);wmFlashMuzzle(&flash,&base);}wmFlashRoll(&flash);wmAddFlash(&flash);'''+extra+'\n')
a='SystemCall(CG_CVAR_UPDATE,&pmGunPosition);SystemCall(CG_CVAR_UPDATE,&pmDebugStance);'
s=rep(s,a,a+'SystemCall(CG_CVAR_UPDATE,&pmFlashHold);')
save(f,s)
print('muzzle flash pass applied to',root)
